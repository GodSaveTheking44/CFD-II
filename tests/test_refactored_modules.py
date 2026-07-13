"""
Unit test suite for the refactored modular CFD package.
Verifies geometry mathematics, coordinate rotations, 
vehicle dynamics physics models, and post-processing parser safety.
"""

import os
import sys
import logging
import unittest
import numpy as np

# Ensure workspace root is in path for relative package imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.geometry import (
    generate_naca4_airfoil,
    rotate_profile_points,
    build_multielement_profile
)
from src.vehicle_dynamics import simulate_straight_line_performance
from src.parser import (
    extract_force_coefficients,
    extract_surface_pressure_distribution,
    extract_wake_velocity_profile
)

class TestGeometry(unittest.TestCase):
    """Verifies geometry coordinates generation, rotations, and wing assemblies."""
    
    def test_naca_airfoil_coordinates_form_closed_loop(self):
        """Confirm that NACA coordinates generated form a closed loop (ends match start)."""
        x_coords, y_coords = generate_naca4_airfoil(0.04, 0.4, 0.12, 1.0, num_points=50)
        
        # Test that the coordinate arrays are non-empty
        self.assertGreater(len(x_coords), 0)
        self.assertEqual(len(x_coords), len(y_coords))
        
        # In a closed CCW loop starting at TE, the first and last points are close to trailing edge (1.0, 0.0)
        self.assertAlmostEqual(x_coords[0], 1.0, places=2)
        self.assertAlmostEqual(x_coords[-1], 1.0, places=2)

    def test_naca_airfoil_respects_chord_scaling(self):
        """Confirm that airfoil chord scaling matches requested length."""
        chord_length = 0.5
        x_coords, _ = generate_naca4_airfoil(0.04, 0.4, 0.12, chord_length, num_points=100)
        
        # Min coordinate should be close to 0 (leading edge), max coordinate near chord length.
        # Use delta because thickness projection at the leading edge can push coordinates slightly negative.
        self.assertAlmostEqual(np.min(x_coords), 0.0, delta=1e-3)
        self.assertAlmostEqual(np.max(x_coords), chord_length, delta=1e-3)

    def test_rotate_profile_points_gives_correct_coordinates(self):
        """Rotate a simple coordinate (1.0, 0.0) clockwise by 90 degrees around origin."""
        x = np.array([1.0])
        y = np.array([0.0])
        
        # Rotating (1.0, 0.0) 90 deg clockwise (which is -90 deg rotation) moves it to (0.0, -1.0)
        rx, ry = rotate_profile_points(x, y, 90.0, pivot_point=(0.0, 0.0))
        
        self.assertAlmostEqual(rx[0], 0.0, places=6)
        self.assertAlmostEqual(ry[0], -1.0, places=6)

    def test_multielement_wing_has_valid_bounds(self):
        """Verify that multi-element wing builds successfully and shifts trailing edge to (0,0)."""
        mainplane, flap1, flap2, _, _ = build_multielement_profile(0.5)
        
        # Verify coordinates are arrays
        self.assertTrue(isinstance(mainplane[0], np.ndarray))
        
        # The mainplane trailing edge (index -1 in CCW coordinates) should be shifted to exactly (0,0)
        self.assertAlmostEqual(mainplane[0][-1], 0.0, places=6)
        self.assertAlmostEqual(mainplane[1][-1], 0.0, places=6)


class TestVehicleDynamics(unittest.TestCase):
    """Verifies numerical integration of vehicle straight-line model."""

    def test_vehicle_dynamics_gives_sensible_and_consistent_results(self):
        """Run straight-line integration and confirm outputs are physical."""
        # Simple drag and lift values
        # X-mode: Cd=0.15, Cl=-1.5
        # Z-mode: Cd=0.45, Cl=-3.5
        stats = simulate_straight_line_performance(0.15, -1.5, 0.45, -3.5)
        
        # Check keys are present
        self.assertIn("x_mode", stats)
        self.assertIn("z_mode", stats)
        
        # X-mode should be faster and complete in less time due to lower drag
        self.assertLess(stats["x_mode"]["time"], stats["z_mode"]["time"])
        self.assertGreater(stats["x_mode"]["top_speed"], stats["z_mode"]["top_speed"])
        self.assertGreater(stats["time_delta"], 0.0)
        self.assertGreater(stats["speed_delta"], 0.0)
        
        # Top speed of modern F1 cars in X-mode should be > 300 km/h but < 400 km/h
        self.assertGreater(stats["x_mode"]["top_speed"], 300.0)
        self.assertLess(stats["x_mode"]["top_speed"], 400.0)


class TestParserSafety(unittest.TestCase):
    """Verifies that parsers handle missing files gracefully rather than crashing."""

    def test_parsers_return_none_when_files_are_missing(self):
        """Ensure parsing non-existent paths returns None without raising errors."""
        bad_path = "./non_existent_folder_xyz"
        
        # Redirect logging to avoid cluttering test outputs
        logging.disable(logging.WARNING)
        
        cd, cl = extract_force_coefficients(bad_path)
        self.assertIsNone(cd)
        self.assertIsNone(cl)
        
        cp_data = extract_surface_pressure_distribution(bad_path)
        self.assertIsNone(cp_data)
        
        wake_data = extract_wake_velocity_profile(bad_path)
        self.assertIsNone(wake_data)
        
        # Restore logging
        logging.disable(logging.NOTSET)


if __name__ == "__main__":
    unittest.main()
