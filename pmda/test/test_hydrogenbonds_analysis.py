# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 fileencoding=utf-8
#
# MDAnalysis --- https://www.mdanalysis.org
# Copyright (c) 2006-2017 The MDAnalysis Development Team and contributors
# (see the file AUTHORS for the full list of names)
#
# Released under the GNU Public Licence, v2 or any higher version
#
# Please cite your use of MDAnalysis in published work:
#
# R. J. Gowers, M. Linke, J. Barnoud, T. J. E. Reddy, M. N. Melo, S. L. Seyler,
# D. L. Dotson, J. Domanski, S. Buchoux, I. M. Kenney, and O. Beckstein.
# MDAnalysis: A Python package for the rapid analysis of molecular dynamics
# simulations. In S. Benthall and S. Rostrup editors, Proceedings of the 15th
# Python in Science Conference, pages 102-109, Austin, TX, 2016. SciPy.
# doi: 10.25080/majora-629e541a-00e
#
# N. Michaud-Agrawal, E. J. Denning, T. B. Woolf, and O. Beckstein.
# MDAnalysis: A Toolkit for the Analysis of Molecular Dynamics Simulations.
# J. Comput. Chem. 32 (2011), 2319--2327, doi:10.1002/jcc.21787
#


from __future__ import absolute_import, division

import numpy as np
import MDAnalysis
from pmda.hbond_analysis import HydrogenBondAnalysis

import pytest
from numpy.testing import assert_allclose
from numpy.testing import assert_array_almost_equal, assert_array_equal
from MDAnalysisTests.datafiles import waterPSF, waterDCD, GRO


class TestHydrogenBondAnalysisTIP3P(object):

    @staticmethod
    @pytest.fixture(scope='class')
    def universe():
        return MDAnalysis.Universe(waterPSF, waterDCD)

    kwargs = {
        'donors_sel': 'name OH2',
        'hydrogens_sel': 'name H1 H2',
        'acceptors_sel': 'name OH2',
        'd_h_cutoff': 1.2,
        'd_a_cutoff': 3.0,
        'd_h_a_angle_cutoff': 120.0
    }

    @pytest.fixture(scope='class')
    def h(self, universe):
        h = HydrogenBondAnalysis(universe, **self.kwargs)
        return h

    @pytest.mark.parametrize("n_blocks", [1, 2, 3, 4, 8])
    def test_hbond_analysis(self, h, n_blocks):
        h.run(n_jobs=n_blocks, n_blocks=n_blocks)
        assert len(np.unique(h.hbonds[:, 0])) == 10
        assert len(h.hbonds) == 32

        reference = {
            'distance': {'mean': 2.7627309, 'std': 0.0905052},
            'angle': {'mean': 158.9038039, 'std': 12.0362826},
        }

        assert_allclose(np.mean(h.hbonds[:, 4]),
                        reference['distance']['mean'])
        assert_allclose(np.std(h.hbonds[:, 4]), reference['distance']['std'])
        assert_allclose(np.mean(h.hbonds[:, 5]), reference['angle']['mean'])
        assert_allclose(np.std(h.hbonds[:, 5]), reference['angle']['std'])

    @pytest.mark.parametrize("n_blocks", [1, 2, 3, 4, 8])
    def test_count_by_time(self, h, n_blocks):
        h.run(n_jobs=n_blocks, n_blocks=n_blocks)
        ref_times = np.arange(0.02, 0.21, 0.02)
        ref_counts = np.array([3, 2, 4, 4, 4, 4, 3, 2, 3, 3])

        counts = h.count_by_time()
        assert_array_almost_equal(h.timesteps, ref_times)
        assert_array_equal(counts, ref_counts)

    def test_count_by_type(self, h):
        h.run(n_jobs=4, n_blocks=4)
        # Only one type of hydrogen bond in this system
        ref_count = 32

        counts = h.count_by_type()
        assert int(counts[0, 2]) == ref_count

    def test_count_by_ids(self, h):
        h.run(n_jobs=4, n_blocks=4)
        ref_counts = [1.0, 1.0, 0.5, 0.4, 0.2, 0.1]
        unique_hbonds = h.count_by_ids()

        # count_by_ids() returns raw counts
        # convert to fraction of time that bond was observed
        counts = unique_hbonds[:, 3] / len(h.timesteps)

        assert_array_equal(counts, ref_counts)

    def test_universe(self, h, universe):
        ref = universe.atoms.positions
        h.run(n_jobs=4, n_blocks=4)
        u = h._universe()
        assert_array_almost_equal(u.atoms.positions, ref)


class TestGuess_UseTopology(TestHydrogenBondAnalysisTIP3P):
    """Uses the same distance and cutoff hydrogen bond criteria as
    :class:`TestHydrogenBondAnalysisTIP3P`, so the results are identical,
    but the hydrogens and acceptors are guessed whilst the donor-hydrogen
    pairs are determined via the topology.
    """
    kwargs = {
        'donors_sel': None,
        'hydrogens_sel': None,
        'acceptors_sel': None,
        'd_a_cutoff': 3.0,
        'd_h_a_angle_cutoff': 120.0
    }


class TestNoUpdating(TestHydrogenBondAnalysisTIP3P):
    """Uses the same distance and cutoff hydrogen bond criteria as
    :class:`TestHydrogenBondAnalysisTIP3P`, but we set `update_selections` to
    be False. The results are identical because the selections are the same
    for each frame for this system.
    """
    kwargs = {
        'donors_sel': None,
        'hydrogens_sel': 'name H1 H2',
        'acceptors_sel': 'name OH2',
        'd_a_cutoff': 3.0,
        'd_h_a_angle_cutoff': 120.0,
        'update_selections': False
    }


class TestGuessDonors_NoTopology(object):
    """Guess the donor atoms involved in hydrogen bonds using the partial
    charges of the atoms.
    """

    @staticmethod
    @pytest.fixture(scope='class')
    def universe():
        return MDAnalysis.Universe(waterPSF, waterDCD)

    kwargs = {
        'donors_sel': None,
        'hydrogens_sel': None,
        'acceptors_sel': None,
        'd_h_cutoff': 1.2,
        'd_a_cutoff': 3.0,
        'd_h_a_angle_cutoff': 120.0
    }

    @pytest.fixture(scope='class')
    def h(self, universe):
        h = HydrogenBondAnalysis(universe, **self.kwargs)
        return h

    def test_guess_donors(self, h):
        ref_donors = "(resname TIP3 and name OH2)"
        donors = h.guess_donors(selection='all', max_charge=-0.5)
        assert donors == ref_donors


class TestGuessDonors_GivenHydrogen(TestGuessDonors_NoTopology):
    """Guess the donor atoms involved in hydrogen bonds using the partial
    charges of the atoms, given hydrogen selections.
    """

    kwargs = {
        'donors_sel': None,
        'hydrogens_sel': 'name H1 H2',
        'acceptors_sel': 'name OH2',
        'd_h_cutoff': 1.2,
        'd_a_cutoff': 3.0,
        'd_h_a_angle_cutoff': 120.0
    }


class TestHydrogenBondAnalysisTIP3PStartStep(object):
    """Uses the same distance and cutoff hydrogen bond criteria as
    :class:`TestHydrogenBondAnalysisTIP3P` but starting with the second
    frame and using every other frame in the analysis.
    """

    @staticmethod
    @pytest.fixture(scope='class')
    def universe():
        return MDAnalysis.Universe(waterPSF, waterDCD)

    kwargs = {
        'donors_sel': 'name OH2',
        'hydrogens_sel': 'name H1 H2',
        'acceptors_sel': 'name OH2',
        'd_h_cutoff': 1.2,
        'd_a_cutoff': 3.0,
        'd_h_a_angle_cutoff': 120.0
    }

    @pytest.fixture(scope='class')
    def h(self, universe):
        h = HydrogenBondAnalysis(universe, **self.kwargs)
        return h

    @pytest.mark.parametrize("n_blocks", [1, 2, 3, 4])
    def test_hbond_analysis(self, h, n_blocks):
        h.run(start=1, step=2, n_jobs=n_blocks, n_blocks=n_blocks)
        assert len(np.unique(h.hbonds[:, 0])) == 5
        assert len(h.hbonds) == 15

        reference = {
            'distance': {'mean': 2.73942464, 'std': 0.05867924},
            'angle': {'mean': 157.07768079, 'std': 9.72636682},
        }

        assert_allclose(np.mean(h.hbonds[:, 4]),
                        reference['distance']['mean'])
        assert_allclose(np.std(h.hbonds[:, 4]), reference['distance']['std'])
        assert_allclose(np.mean(h.hbonds[:, 5]), reference['angle']['mean'])
        assert_allclose(np.std(h.hbonds[:, 5]), reference['angle']['std'])

    @pytest.mark.parametrize("n_blocks", [1, 2, 3, 4])
    def test_count_by_time(self, h, n_blocks):
        h.run(start=1, step=2, n_jobs=n_blocks, n_blocks=n_blocks)
        ref_times = np.array([0.04, 0.08, 0.12, 0.16, 0.20, ])
        ref_counts = np.array([2, 4, 4, 2, 3])

        counts = h.count_by_time()
        assert_array_almost_equal(h.timesteps, ref_times)
        assert_array_equal(counts, ref_counts)

    def test_count_by_type(self, h):
        h.run(start=1, step=2, n_jobs=4, n_blocks=4)
        # Only one type of hydrogen bond in this system
        ref_count = 15

        counts = h.count_by_type()
        assert int(counts[0, 2]) == ref_count


class TestNoBond_Topology(object):
    """Use the topology file that has positions information, but doesn't have
    bonds information.
    """

    kwargs = {
        'donors_sel': None,
        'hydrogens_sel': None,
        'acceptors_sel': None,
        'd_h_cutoff': 1.2,
        'd_a_cutoff': 3.0,
        'd_h_a_angle_cutoff': 120.0
    }

    def test_nobond(self):
        u = MDAnalysis.Universe(GRO)
        h = HydrogenBondAnalysis(u, **self.kwargs)
        with pytest.raises(ValueError):
            h._get_dh_pairs(u)

    def test_universe(self):
        universe = MDAnalysis.Universe(GRO)
        ref = universe.atoms.positions
        h = HydrogenBondAnalysis(universe, **self.kwargs)
        u = h._universe()
        assert_array_almost_equal(u.atoms.positions, ref)
