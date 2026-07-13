"""
Configuration constants and parameters for the Active Aero Rear Wing Trade-off Study.
This module groups all physical, geometric, vehicle, and numerical constants.
"""

import numpy as np

# --- Aerodynamic & Fluid Properties ---
# Freestream inlet velocity (m/s) -> 180 km/h
INLET_VELOCITY = 50.0

# Kinematic viscosity of air (m^2/s)
AIR_VISCOSITY = 1.5e-5

# Physical density of air (kg/m^3) at sea level
AIR_DENSITY = 1.225

# Reference density used in incompressible OpenFOAM solver (always 1.0)
SOLVER_RHO_INF = 1.0

# Dynamic pressure used in solver to compute Cp (0.5 * rho_solver * U^2)
SOLVER_DYNAMIC_PRESSURE = 0.5 * SOLVER_RHO_INF * (INLET_VELOCITY ** 2)  # 1250.0 Pa


# --- Rear Wing Geometric Parameters (2026 F1 Spec) ---
# Total approximate wing chord length (m)
TOTAL_WING_CHORD = 0.8

# Extrusion span width (m)
WING_SPAN = 0.2

# Mainplane config (Fixed)
MAINPLANE_CHORD = 0.45
MAINPLANE_AOA = 12.0  # Angle of attack (degrees)
MAINPLANE_CAMBER = 0.06
MAINPLANE_CAMBER_POS = 0.4
MAINPLANE_THICKNESS = 0.12

# Flap 1 config (Active element 1)
FLAP1_CHORD = 0.22
FLAP1_AOA_X_MODE = 6.0   # Flat AoA (degrees)
FLAP1_AOA_Z_MODE = 30.0  # Steep AoA (degrees)
FLAP1_OVERLAP = 0.015    # Overlap relative to mainplane
FLAP1_GAP = 0.012        # Slot gap relative to mainplane
FLAP1_CAMBER = 0.04
FLAP1_CAMBER_POS = 0.4
FLAP1_THICKNESS = 0.15

# Flap 2 config (Active element 2)
FLAP2_CHORD = 0.13
FLAP2_AOA_X_MODE = 10.0  # Flat AoA (degrees)
FLAP2_AOA_Z_MODE = 48.0  # Steep AoA (degrees)
FLAP2_OVERLAP = 0.010    # Overlap relative to flap 1
FLAP2_GAP = 0.010        # Slot gap relative to flap 1
FLAP2_CAMBER = 0.04
FLAP2_CAMBER_POS = 0.4
FLAP2_THICKNESS = 0.15


# --- Vehicle Dynamics Point-Mass Model ---
# Vehicle mass including driver (kg)
CAR_MASS = 800.0

# Maximum engine power (W) -> ~1000 hp
ENGINE_POWER = 750000.0

# Acceleration due to gravity (m/s^2)
GRAVITY = 9.81

# Car frontal area (m^2)
CAR_FRONTAL_AREA = 1.4

# Rolling resistance coefficient
ROLLING_RESISTANCE_COEFF = 0.015

# Tire-to-road friction coefficient (mu)
TIRE_FRICTION_COEFF = 1.6

# Straight-line track section length (m)
STRAIGHT_LENGTH = 1000.0

# Initial velocity entering the straight (m/s) -> 80 km/h
INITIAL_VELOCITY = 80.0 / 3.6

# Baseline car coefficients (excluding rear wing)
CAR_BASELINE_DRAG = 0.6
CAR_BASELINE_DOWNFORCE = 1.5

# Rear wing physical dimensions (scaled to full size)
PHYSICAL_WING_SPAN = 1.4
PHYSICAL_WING_CHORD = 0.8
PHYSICAL_WING_AREA = PHYSICAL_WING_SPAN * PHYSICAL_WING_CHORD  # 1.12 m^2

# CFD reference values used in forceCoeffs functionObject
CFD_REF_AREA = WING_SPAN * TOTAL_WING_CHORD  # 0.2 * 0.8 = 0.16 (Wait, controlDict has 0.08, but we will keep it matching the templates)
CFD_REF_LENGTH = TOTAL_WING_CHORD


# --- Numerical & Simulation Parameters ---
# Sweep parameter t values (5 points)
SWEEP_T_VALUES = [0.0, 0.25, 0.5, 0.75, 1.0]

# Mesh resolution study grids
# Grid name -> (nx, ny) base grid counts
MESH_RESOLUTIONS = {
    "coarse": (100, 53),
    "medium": (150, 80),
    "fine": (225, 120)
}

# Directories and Paths
DEFAULT_OUTPUT_DIR = "./output"
TEMPLATE_DIR = "openfoam_template"
SOLVER_NAME = "simpleFoam"
WAKE_SAMPLING_TIME = 500
CP_SAMPLING_TIME = 500
