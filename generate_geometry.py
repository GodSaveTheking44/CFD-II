#!/usr/bin/env python3
"""
CLI entrypoint for 2026 F1 Rear Wing geometry generation.
Delegates core geometry calculations and STL writing to the src.geometry module.
"""

import sys
import os
import argparse
import numpy as np

# Ensure workspace root is in path for relative package imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.geometry import (
    build_multielement_profile,
    extrude_and_triangulate_profile,
    export_stl_file
)

def main():
    parser = argparse.ArgumentParser(description="Generate 2026 F1 Rear Wing STL geometry.")
    parser.add_argument("-t", "--sweep", type=float, default=1.0, 
                        help="Sweep parameter: 0.0=X-mode (flat), 1.0=Z-mode (steep)")
    parser.add_argument("-o", "--output", type=str, default="wing.stl", 
                        help="Output STL file path (default: wing.stl)")
    parser.add_argument("-s", "--span", type=float, default=0.2, 
                        help="Extrusion span in meters (default: 0.2)")
    args = parser.parse_args()
    
    sweep_param = np.clip(args.sweep, 0.0, 1.0)
    span = args.span
    z_min, z_max = -span / 2.0, span / 2.0
    
    print(f"Generating F1 wing geometry for sweep parameter t = {sweep_param:.2f}...")
    try:
        # 1. Build 2D elements and rotate
        mainplane, flap1, flap2, flap1_aoa, flap2_aoa = build_multielement_profile(sweep_param)
        print(f"Resolved angles: Flap 1 AoA = {flap1_aoa:.2f} deg, Flap 2 AoA = {flap2_aoa:.2f} deg")
        
        # 2. Extrude profiles to 3D and triangulate caps/lateral boundaries
        facets_main = extrude_and_triangulate_profile(mainplane[0], mainplane[1], z_min, z_max)
        facets_flap1 = extrude_and_triangulate_profile(flap1[0], flap1[1], z_min, z_max)
        facets_flap2 = extrude_and_triangulate_profile(flap2[0], flap2[1], z_min, z_max)
        
        all_facets = facets_main + facets_flap1 + facets_flap2
        
        # 3. Export to target file
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        export_stl_file(args.output, all_facets)
        print(f"Watertight STL successfully written to: {args.output}")
        print(f"Total facets generated: {len(all_facets)}")
    except Exception as e:
        print(f"Error during geometry generation: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
