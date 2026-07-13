#!/usr/bin/env python3
"""
Active Aero Rear Wing Sweep and Optimization Pipeline.
Main execution script coordinating parametric runs, mesh convergence checks,
vehicle dynamics integrations, plotting, and markdown report compiling.
"""

import os
import sys
import argparse
import logging

# Ensure root directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import (
    SWEEP_T_VALUES, MESH_RESOLUTIONS, DEFAULT_OUTPUT_DIR,
    WAKE_SAMPLING_TIME, CP_SAMPLING_TIME
)
from src.openfoam import (
    initialize_openfoam_case,
    execute_openfoam_pipeline,
    query_cell_count
)
from src.parser import (
    extract_force_coefficients,
    extract_surface_pressure_distribution,
    extract_wake_velocity_profile
)
from src.vehicle_dynamics import simulate_straight_line_performance
from src.plotting import (
    plot_polar_curve,
    plot_mesh_convergence,
    plot_pressure_distribution,
    plot_wake_deficit
)
from src.report import generate_markdown_report

# Configure logger at the entrypoint
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("run_sweep")

def run_pipeline(output_dir, skip_simulations=False):
    """
    Run the entire active aero study pipeline.
    
    Args:
        output_dir (str): Host-facing output directory for report/plots
        skip_simulations (bool): If True, skip OpenFOAM runs and parse existing cases
    """
    logger.info("Initializing F1 Active Aero optimization pipeline...")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Run Simulations (or verify they exist)
    if not skip_simulations:
        logger.info("Executing simulation sweeps in OpenFOAM...")
        try:
            # A. Run mesh independence study cases (Coarse, Medium, Fine for t=0.0 and t=1.0)
            for grid_name, (nx, ny) in MESH_RESOLUTIONS.items():
                for t_val in [0.0, 1.0]:
                    case_dir = f"case_mesh_{grid_name}_t_{t_val:.2f}"
                    logger.info("Setting up grid study case: %s", case_dir)
                    initialize_openfoam_case(case_dir, t_val, nx, ny)
                    execute_openfoam_pipeline(case_dir)
                    
            # B. Run intermediate sweep cases (t=0.25, 0.50, 0.75) using Medium mesh
            medium_nx, medium_ny = MESH_RESOLUTIONS["medium"]
            for t_val in [0.25, 0.50, 0.75]:
                case_dir = f"case_t_{t_val:.2f}"
                logger.info("Setting up sweep case: %s", case_dir)
                initialize_openfoam_case(case_dir, t_val, medium_nx, medium_ny)
                execute_openfoam_pipeline(case_dir)
        except Exception as e:
            logger.critical("CFD pipeline execution failed: %s", str(e))
            sys.exit(1)
    else:
        logger.info("Skipping OpenFOAM execution; reading cached files from disk.")
        
    # 2. Parse Results
    logger.info("Parsing force coefficients and simulation outputs...")
    
    # Parse mesh study data
    mesh_study_results = {0.0: [], 1.0: []}
    for t_val in [0.0, 1.0]:
        for grid_name in MESH_RESOLUTIONS.keys():
            case_dir = f"case_mesh_{grid_name}_t_{t_val:.2f}"
            cells = query_cell_count(case_dir)
            cd_val, cl_val = extract_force_coefficients(case_dir)
            
            if cells is not None and cd_val is not None and cl_val is not None:
                mesh_study_results[t_val].append({
                    "resolution": grid_name,
                    "cells": cells,
                    "Cd": cd_val,
                    "Cl": cl_val
                })
            else:
                logger.warning("Incomplete mesh study data in %s", case_dir)
                
    # Parse sweep results
    sweep_results = []
    for t_val in SWEEP_T_VALUES:
        # Match case directories
        if t_val == 0.0:
            case_dir = "case_mesh_medium_t_0.00"
        elif t_val == 1.0:
            case_dir = "case_mesh_medium_t_1.00"
        else:
            case_dir = f"case_t_{t_val:.2f}"
            
        cd_val, cl_val = extract_force_coefficients(case_dir)
        
        # Calculate actual flap AoA values for reporting
        flap1_aoa = 6.0 + t_val * 24.0
        flap2_aoa = 10.0 + t_val * 38.0
        
        if cd_val is not None and cl_val is not None:
            sweep_results.append({
                "t": t_val,
                "aoa2": flap1_aoa,
                "aoa3": flap2_aoa,
                "Cd": cd_val,
                "Cl": cl_val
            })
        else:
            logger.error("Missing sweep results for t=%.2f (searched %s)", t_val, case_dir)
            
    if not sweep_results:
        logger.critical("No sweep results parsed. Cannot proceed with report compilation.")
        sys.exit(1)
        
    # Print results summary to console
    logger.info("Sweep Summary:")
    for r in sweep_results:
        efficiency = -r["Cl"] / r["Cd"] if r["Cd"] != 0 else 0
        logger.info(
            "t=%.2f (Flaps %.1f/%.1f deg) -> Cd = %.4f, Cl = %.4f, L/D = %.3f",
            r["t"], r["aoa2"], r["aoa3"], r["Cd"], r["Cl"], efficiency
        )
        
    # 3. Post-Process & Plotting
    logger.info("Generating presentation figures...")
    
    # Plot polar curve
    plot_polar_curve(sweep_results, output_dir)
    
    # Plot mesh convergence
    plot_mesh_convergence(mesh_study_results, output_dir)
    
    # Parse and plot Cp distributions at sweep extremes
    case_x_mode = "case_mesh_medium_t_0.00"
    case_z_mode = "case_mesh_medium_t_1.00"
    
    cp_data_x = extract_surface_pressure_distribution(case_x_mode, CP_SAMPLING_TIME)
    cp_data_z = extract_surface_pressure_distribution(case_z_mode, CP_SAMPLING_TIME)
    plot_pressure_distribution(cp_data_x, cp_data_z, output_dir)
    
    # Parse and plot wake deficit profiles
    wake_data_x = extract_wake_velocity_profile(case_x_mode, WAKE_SAMPLING_TIME)
    wake_data_z = extract_wake_velocity_profile(case_z_mode, WAKE_SAMPLING_TIME)
    plot_wake_deficit(wake_data_x, wake_data_z, output_dir)
    
    # 4. Run Vehicle Dynamics Model
    try:
        cd_x = next(r["Cd"] for r in sweep_results if r["t"] == 0.0)
        cl_x = next(r["Cl"] for r in sweep_results if r["t"] == 0.0)
        cd_z = next(r["Cd"] for r in sweep_results if r["t"] == 1.0)
        cl_z = next(r["Cl"] for r in sweep_results if r["t"] == 1.0)
    except StopIteration:
        logger.critical("Sweep data is missing critical endpoints (t=0.0 or t=1.0)")
        sys.exit(1)
        
    vehicle_stats = simulate_straight_line_performance(cd_x, cl_x, cd_z, cl_z)
    
    logger.info("1000m Straight Acceleration Results:")
    logger.info("X-mode (low drag): Final Speed = %.2f km/h, Time = %.3fs", 
                vehicle_stats["x_mode"]["top_speed"], vehicle_stats["x_mode"]["time"])
    logger.info("Z-mode (high downforce): Final Speed = %.2f km/h, Time = %.3fs", 
                vehicle_stats["z_mode"]["top_speed"], vehicle_stats["z_mode"]["time"])
    logger.info("Aerodynamic Advantage: Time Saved = -%.3fs, Top Speed Boost = +%.2f km/h",
                vehicle_stats["time_delta"], vehicle_stats["speed_delta"])
                
    # 5. Compile and Write Report
    report_filepath = os.path.join(output_dir, "report.md")
    generate_markdown_report(report_filepath, sweep_results, mesh_study_results, vehicle_stats)
    logger.info("Pipeline executed successfully. Outputs saved to: %s", output_dir)

def main():
    parser = argparse.ArgumentParser(description="Automate active aero rear wing sweep and optimization.")
    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT_DIR, 
                        help=f"Target directory for output plots and report (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--skip-sim", action="store_true", 
                        help="Skip OpenFOAM calculations and perform parsing and post-processing only")
    parser.add_argument("--debug", action="store_true", 
                        help="Enable detailed debug logs")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled.")
        
    run_pipeline(args.output, args.skip_sim)

if __name__ == "__main__":
    main()
