from app.services.vegetation_index import (
    sar_index_from_vv_db,
    index_family_for_tier,
    effective_std,
)


def test_sar_index_from_vv_db_maps_typical_range():
    # -22 dB (bare/rough ground) -> 0.0, -4 dB (dense canopy-like backscatter) -> 1.0
    assert sar_index_from_vv_db(-22.0) == 0.0
    assert sar_index_from_vv_db(-4.0) == 1.0


def test_sar_index_from_vv_db_clamps_out_of_range_values():
    assert sar_index_from_vv_db(-30.0) == 0.0
    assert sar_index_from_vv_db(10.0) == 1.0


def test_sar_index_from_vv_db_midpoint():
    # halfway between -22 and -4 should land at 0.5
    assert sar_index_from_vv_db(-13.0) == 0.5


def test_index_family_for_tier():
    assert index_family_for_tier("tier3_sar") == "sar"
    assert index_family_for_tier("tier2_sen2sr") == "optical"
    assert index_family_for_tier("tier1_planet") == "optical"


def test_effective_std_floors_near_zero_spread():
    # a near-zero historical std shouldn't produce absurd z-scores
    assert effective_std(mean=0.6, std=0.0001) == 0.6 * 0.08


def test_effective_std_keeps_a_genuinely_large_std():
    assert effective_std(mean=0.6, std=0.2) == 0.2


def test_effective_std_has_an_absolute_floor():
    assert effective_std(mean=0.0, std=0.0) == 0.015
