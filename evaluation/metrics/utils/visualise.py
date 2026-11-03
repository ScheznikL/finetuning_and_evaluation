
import numpy as np
import os

# def visualize_slices(mesh, slices: dict, measurements: dict, output_dir: str, 
#                      uuid: str, min_y: float, max_y: float, height: float):
#     """
#     Create visualization images of mesh slices.
#     Saves PNG images showing the cross-sections.
#     """
#     import matplotlib.pyplot as plt
#     import matplotlib
#     matplotlib.use('Agg')  # Use non-interactive backend
    
#     # Create visualization directory
#     viz_dir = os.path.join(output_dir, 'slice_visualizations', uuid)
#     os.makedirs(viz_dir, exist_ok=True)
    
#     # Create figure with multiple subplots
#     fig, axes = plt.subplots(2, 2, figsize=(14, 14))
#     fig.suptitle(f'Model Slices - UUID: {uuid}\nHeight: {height:.2f} mm', 
#                  fontsize=14, fontweight='bold')
    
#     # 1. Top slice
#     ax = axes[0, 0]
#     if 'top' in slices and slices['top']:
#         plot_2d_slice(ax, slices['top'], 'Top Slice (98%)', 
#                      measurements.get('top_width', 0))
#     else:
#         ax.text(0.5, 0.5, 'No top slice', ha='center', va='center')
#         ax.set_title('Top Slice (98%)')
    
#     # 2. Middle slice
#     ax = axes[0, 1]
#     if 'middle' in slices and slices['middle']:
#         plot_2d_slice(ax, slices['middle'], 'Middle Slice (50%)', 
#                      measurements.get('middle_width', 0))
#     else:
#         ax.text(0.5, 0.5, 'No middle slice', ha='center', va='center')
#         ax.set_title('Middle Slice (50%)')
    
#     # 3. Bottom slice
#     ax = axes[1, 0]
#     if 'bottom' in slices and slices['bottom']:
#         plot_2d_slice(ax, slices['bottom'], 'Bottom Slice (2%)', 
#                      measurements.get('bottom_width', 0))
#     else:
#         ax.text(0.5, 0.5, 'No bottom slice', ha='center', va='center')
#         ax.set_title('Bottom Slice (2%)')
    
#     # 4. Measurements summary
#     ax = axes[1, 1]
#     ax.axis('off')
#     summary_text = f"""
# MEASUREMENTS (mm):

# Total Length: {measurements.get('total_length', 0):.2f}
# Width (X): {measurements.get('width_x', 0):.2f}
# Depth (Z): {measurements.get('depth_z', 0):.2f}

# Top Width: {measurements.get('top_width', 0):.2f}
# Middle Width: {measurements.get('middle_width', 0):.2f}
# Bottom Width: {measurements.get('bottom_width', 0):.2f}
# Channel Depth: {measurements.get('channel_depth', 0):.2f}
#     """
#     ax.text(0.1, 0.5, summary_text, fontsize=12, family='monospace',
#             verticalalignment='center')
    
#     plt.tight_layout()
    
#     # Save figure
#     output_path = os.path.join(viz_dir, 'slices_overview.png')
#     plt.savefig(output_path, dpi=150, bbox_inches='tight')
#     plt.close()
    
#     print(f"  📊 Saved visualization: {output_path}")
    
#     # Also save a 3D view
#     try:
#         from mpl_toolkits.mplot3d import Axes3D
        
#         fig = plt.figure(figsize=(12, 10))
#         ax = fig.add_subplot(111, projection='3d')
        
#         # Plot mesh
#         ax.plot_trisurf(mesh.vertices[:, 0], mesh.vertices[:, 1], 
#                        mesh.vertices[:, 2], triangles=mesh.faces,
#                        alpha=0.3, edgecolor='none', color='lightblue')
        
#         # Add slice planes
#         y_levels = {
#             'Top (98%)': max_y - ((max_y - min_y) * 0.02),
#             'Middle (50%)': (max_y + min_y) / 2,
#             'Bottom (2%)': min_y + ((max_y - min_y) * 0.02)
#         }
        
#         colors = {'Top (98%)': 'red', 'Middle (50%)': 'green', 'Bottom (2%)': 'blue'}
        
#         for label, y_pos in y_levels.items():
#             # Create plane grid
#             x_range = np.linspace(mesh.bounds[0][0], mesh.bounds[1][0], 10)
#             z_range = np.linspace(mesh.bounds[0][2], mesh.bounds[1][2], 10)
#             X, Z = np.meshgrid(x_range, z_range)
#             Y = np.ones_like(X) * y_pos
#             ax.plot_surface(X, Y, Z, alpha=0.3, color=colors[label])
        
        
#         # ax.set_xlabel('X (m)')
#         # ax.set_ylabel('Y (m) - Length')
#         # ax.set_zlabel('Z (m)')
#          # FIX: Set proper axis labels and orientation
#         ax.set_xlabel('X (Width) [m]')
#         ax.set_ylabel('Y (Length/Height) [m]')  # Y is vertical
#         ax.set_zlabel('Z (Depth) [m]')
        
#         # FIX: Set viewing angle so Y points up
#         # elev = elevation angle (view from above), azim = azimuth (rotation around vertical)
#         ax.view_init(elev=20, azim=45)  # Look from slightly above and at 45° angle
        
#         # FIX: Make Y-axis point upward visually by setting equal aspect
#         # Get the range of each axis
#         x_range = mesh.bounds[1][0] - mesh.bounds[0][0]
#         y_range = mesh.bounds[1][1] - mesh.bounds[0][1]
#         z_range = mesh.bounds[1][2] - mesh.bounds[0][2]
        
#          # Set equal aspect ratio based on max range
#         max_range = max(x_range, y_range, z_range)
#         mid_x = (mesh.bounds[1][0] + mesh.bounds[0][0]) / 2
#         mid_y = (mesh.bounds[1][1] + mesh.bounds[0][1]) / 2
#         mid_z = (mesh.bounds[1][2] + mesh.bounds[0][2]) / 2
        
#         ax.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
#         ax.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
#         ax.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
        
#         ax.set_title('3D Model with Slice Planes\n(Y-axis = Length/Height)', fontsize=12, fontweight='bold')
        
        
#         #ax.set_title('3D Model with Slice Planes')
        
#         output_3d_path = os.path.join(viz_dir, '3d_view_with_planes.png')
#         plt.savefig(output_3d_path, dpi=150, bbox_inches='tight')
#         plt.close()
        
#         print(f"  📊 Saved 3D view: {output_3d_path}")
#     except Exception as e:
#         print(f"  ⚠️  Could not create 3D view: {e}")


# def plot_2d_slice(ax, slice_2d, title: str, width: float):
#     """
#     Plot a 2D slice on the given matplotlib axis.
#     """
#     if slice_2d is None:
#         ax.text(0.5, 0.5, 'No slice', ha='center', va='center')
#         ax.set_title(title)
#         return
    
#     # Get vertices from the 2D slice
#     # vertices = slice_2d.vertices
#     vertices = slice_2d.vertices * 100.0
    
#     if len(vertices) == 0:
#         ax.text(0.5, 0.5, 'Empty slice', ha='center', va='center')
#         ax.set_title(title)
#         return
    
#     # Plot the 2D cross-section
#     for entity in slice_2d.entities:
#         # Get points for this entity
#         points = vertices[entity.points]
#         # Close the loop
#         points_closed = np.vstack([points, points[0]])
#         ax.plot(points_closed[:, 0], points_closed[:, 1], 'b-', linewidth=2)
    
#     # Plot all vertices
#     ax.scatter(vertices[:, 0], vertices[:, 1], c='red', s=20, alpha=0.6, zorder=5)
    
#     # Add width annotation
#     if width > 0:
#         ax.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
#         ax.axvline(x=0, color='gray', linestyle='--', alpha=0.3)
        
#         # Show width dimension
#         x_min, x_max = vertices[:, 0].min(), vertices[:, 0].max()
#         y_annotation = vertices[:, 1].min() - 0.015
#         ax.annotate('', xy=(x_max, y_annotation), 
#                    xytext=(x_min, y_annotation),
#                    arrowprops=dict(arrowstyle='<->', color='green', lw=2.5))
     
#         # ax.text((x_min + x_max) / 2, y_annotation - 0.005, 
#         #        f'{width:.2f} mm', ha='center', color='green', 
#         #        fontweight='bold', fontsize=10)
#         ax.text((x_min + x_max) / 2, y_annotation - 0.005, 
#                f'{width/10:.2f} cm', ha='center', color='green', 
#                fontweight='bold', fontsize=10)
    
#     ax.set_aspect('equal')
#     ax.grid(True, alpha=0.3)

# #    ax.set_title(f'{title}\nWidth: {width:.2f} mm', fontsize=11, fontweight='bold')
#     ax.set_title(f'{title}\nWidth: {width/10:.2f} cm', fontsize=11, fontweight='bold')

#     ax.set_xlabel('X (cm)', fontsize=10)
#     ax.set_ylabel('Z (cm)', fontsize=10)
#     # ax.set_xlabel('X (m)', fontsize=10)
#     # ax.set_ylabel('Z (m)', fontsize=10)


def visualize_slices_upright(mesh, slices: dict, measurements: dict, output_dir: str, 
                     uuid: str, min_y: float, max_y: float, height: float,
                     view_elev: float = 20, view_azim: float = 90):
    """
    Create visualization images of mesh slices.
    Saves PNG images showing the cross-sections.
    
    Args:
        mesh: The 3D mesh object
        slices: Dictionary of slice objects
        measurements: Dictionary of measurements
        output_dir: Directory to save visualizations
        uuid: UUID for naming files
        min_y: Minimum Y bound
        max_y: Maximum Y bound
        height: Total height
        view_elev: Elevation angle for 3D view (degrees)
        view_azim: Azimuth angle for 3D view (degrees)
    """
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    
    # Create visualization directory
    viz_dir = os.path.join(output_dir, 'slice_visualizations', uuid)
    os.makedirs(viz_dir, exist_ok=True)
    
    # Determine how many slices we have
    has_5pct = 'top_5pct' in slices or 'bottom_5pct' in slices
    
    if has_5pct:
        # Create figure with 3x2 grid for all slices
        fig, axes = plt.subplots(3, 2, figsize=(14, 18))
        fig.suptitle(f'Model Slices - UUID: {uuid}\nHeight: {height:.2f} mm', 
                     fontsize=14, fontweight='bold')
        
        # Row 1: Top slices
        ax = axes[0, 0]
        if 'top_2pct' in slices and slices['top_2pct']:
            plot_2d_slice(ax, slices['top_2pct'], 'Top Slice (2%)', 
                         measurements.get('top_width_2pct', 0))
        else:
            ax.text(0.5, 0.5, 'No top 2% slice', ha='center', va='center')
            ax.set_title('Top Slice (2%)')
        
        ax = axes[0, 1]
        if 'top_5pct' in slices and slices['top_5pct']:
            plot_2d_slice(ax, slices['top_5pct'], 'Top Slice (5%)', 
                         measurements.get('top_width_5pct', 0))
        else:
            ax.text(0.5, 0.5, 'No top 5% slice', ha='center', va='center')
            ax.set_title('Top Slice (5%)')
        
        # Row 2: Middle and measurements
        ax = axes[1, 0]
        if 'middle' in slices and slices['middle']:
            plot_2d_slice(ax, slices['middle'], 'Middle Slice (50%)', 
                         measurements.get('middle_width', 0))
        else:
            ax.text(0.5, 0.5, 'No middle slice', ha='center', va='center')
            ax.set_title('Middle Slice (50%)')
        
        # Measurements summary
        ax = axes[1, 1]
        ax.axis('off')
        
        # Build summary text with normalization details
        summary_text = f"""
MEASUREMENTS (mm):

Total Length: {measurements.get('total_length', 0):.2f}
Width (X): {measurements.get('width_x', 0):.2f}
Depth (Z): {measurements.get('depth_z', 0):.2f}

Top Width (2%): {measurements.get('top_width_2pct', 0):.2f}
Top Width (5%): {measurements.get('top_width_5pct', 0):.2f}
Middle Width: {measurements.get('middle_width', 0):.2f}
Bottom Width (5%): {measurements.get('bottom_width_5pct', 0):.2f}
Bottom Width (2%): {measurements.get('bottom_width_2pct', 0):.2f}
Channel Depth: {measurements.get('channel_depth', 0):.2f}

Normalized: {measurements.get('normalized', False)}"""
        
        # Add original extents if normalized
        if measurements.get('normalized', False) and measurements.get('original_extents_mm'):
            orig_ext = measurements['original_extents_mm']
            summary_text += f"""

ORIGINAL EXTENTS:
X: {orig_ext[0]:.2f} mm
Y: {orig_ext[1]:.2f} mm
Z: {orig_ext[2]:.2f} mm"""
        
        ax.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
                verticalalignment='center')
        
        # Row 3: Bottom slices
        ax = axes[2, 0]
        if 'bottom_2pct' in slices and slices['bottom_2pct']:
            plot_2d_slice(ax, slices['bottom_2pct'], 'Bottom Slice (2%)', 
                         measurements.get('bottom_width_2pct', 0))
        else:
            ax.text(0.5, 0.5, 'No bottom 2% slice', ha='center', va='center')
            ax.set_title('Bottom Slice (2%)')
        
        ax = axes[2, 1]
        if 'bottom_5pct' in slices and slices['bottom_5pct']:
            plot_2d_slice(ax, slices['bottom_5pct'], 'Bottom Slice (5%)', 
                         measurements.get('bottom_width_5pct', 0))
        else:
            ax.text(0.5, 0.5, 'No bottom 5% slice', ha='center', va='center')
            ax.set_title('Bottom Slice (5%)')
    
    else:
        # Original 2x2 layout for backward compatibility
        fig, axes = plt.subplots(2, 2, figsize=(14, 14))
        fig.suptitle(f'Model Slices - UUID: {uuid}\nHeight: {height:.2f} mm', 
                     fontsize=14, fontweight='bold')
        
        # 1. Top slice
        ax = axes[0, 0]
        if 'top_2pct' in slices and slices['top_2pct']:
            plot_2d_slice(ax, slices['top_2pct'], 'Top Slice (2%)', 
                         measurements.get('top_width_2pct', measurements.get('top_width', 0)))
        elif 'top' in slices and slices['top']:
            plot_2d_slice(ax, slices['top'], 'Top Slice (98%)', 
                         measurements.get('top_width', 0))
        else:
            ax.text(0.5, 0.5, 'No top slice', ha='center', va='center')
            ax.set_title('Top Slice')
        
        # 2. Middle slice
        ax = axes[0, 1]
        if 'middle' in slices and slices['middle']:
            plot_2d_slice(ax, slices['middle'], 'Middle Slice (50%)', 
                         measurements.get('middle_width', 0))
        else:
            ax.text(0.5, 0.5, 'No middle slice', ha='center', va='center')
            ax.set_title('Middle Slice (50%)')
        
        # 3. Bottom slice
        ax = axes[1, 0]
        if 'bottom_2pct' in slices and slices['bottom_2pct']:
            plot_2d_slice(ax, slices['bottom_2pct'], 'Bottom Slice (2%)', 
                         measurements.get('bottom_width_2pct', measurements.get('bottom_width', 0)))
        elif 'bottom' in slices and slices['bottom']:
            plot_2d_slice(ax, slices['bottom'], 'Bottom Slice (2%)', 
                         measurements.get('bottom_width', 0))
        else:
            ax.text(0.5, 0.5, 'No bottom slice', ha='center', va='center')
            ax.set_title('Bottom Slice')
        
        # 4. Measurements summary
        ax = axes[1, 1]
        ax.axis('off')
        
        # Build summary text
        summary_text = f"""
MEASUREMENTS (mm):

Total Length: {measurements.get('total_length', 0):.2f}
Width (X): {measurements.get('width_x', 0):.2f}
Depth (Z): {measurements.get('depth_z', 0):.2f}

Top Width: {measurements.get('top_width', 0):.2f}
Middle Width: {measurements.get('middle_width', 0):.2f}
Bottom Width: {measurements.get('bottom_width', 0):.2f}
Channel Depth: {measurements.get('channel_depth', 0):.2f}

Normalized: {measurements.get('normalized', False)}"""
        
        # Add original extents if normalized
        if measurements.get('normalized', False) and measurements.get('original_extents_mm'):
            orig_ext = measurements['original_extents_mm']
            summary_text += f"""

ORIGINAL EXTENTS:
X: {orig_ext[0]:.2f} mm
Y: {orig_ext[1]:.2f} mm
Z: {orig_ext[2]:.2f} mm"""
        
        ax.text(0.1, 0.5, summary_text, fontsize=11, family='monospace',
                verticalalignment='center')
    
    plt.tight_layout()
    
    # Save figure
    output_path = os.path.join(viz_dir, 'slices_overview.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  📊 Saved visualization: {output_path}")
    
    # Also save a 3D view with profile orientation
    try:
        from mpl_toolkits.mplot3d import Axes3D
        
        fig = plt.figure(figsize=(16, 10))
        
        # Create two subplots: 3D view and profile view
        ax1 = fig.add_subplot(121, projection='3d')
        ax2 = fig.add_subplot(122, projection='3d')
        
        # === LEFT PLOT: User-controlled 3D view ===
        ax1.plot_trisurf(mesh.vertices[:, 0], mesh.vertices[:, 1], 
                       mesh.vertices[:, 2], triangles=mesh.faces,
                       alpha=0.3, edgecolor='none', color='lightblue')
        
        # Add all available slice levels to 3D view
        y_levels = {}
        colors = {}
        
        if 'top_2pct' in slices:
            y_levels['Top (2%)'] = max_y - ((max_y - min_y) * 0.02)
            colors['Top (2%)'] = 'red'
        
        if 'top_5pct' in slices:
            y_levels['Top (5%)'] = max_y - ((max_y - min_y) * 0.05)
            colors['Top (5%)'] = 'orange'
        
        if 'middle' in slices:
            y_levels['Middle (50%)'] = (max_y + min_y) / 2
            colors['Middle (50%)'] = 'green'
        
        if 'bottom_5pct' in slices:
            y_levels['Bottom (5%)'] = min_y + ((max_y - min_y) * 0.05)
            colors['Bottom (5%)'] = 'cyan'
        
        if 'bottom_2pct' in slices:
            y_levels['Bottom (2%)'] = min_y + ((max_y - min_y) * 0.02)
            colors['Bottom (2%)'] = 'blue'
        
        # Fallback to old naming convention
        if not y_levels and 'top' in slices:
            y_levels['Top (98%)'] = max_y - ((max_y - min_y) * 0.02)
            colors['Top (98%)'] = 'red'
        if not y_levels and 'bottom' in slices:
            y_levels['Bottom (2%)'] = min_y + ((max_y - min_y) * 0.02)
            colors['Bottom (2%)'] = 'blue'
        
        # Draw slice planes in 3D view
        for label, y_pos in y_levels.items():
            x_range = np.linspace(mesh.bounds[0][0], mesh.bounds[1][0], 10)
            z_range = np.linspace(mesh.bounds[0][2], mesh.bounds[1][2], 10)
            X, Z = np.meshgrid(x_range, z_range)
            Y = np.ones_like(X) * y_pos
            ax1.plot_surface(X, Y, Z, alpha=0.3, color=colors[label])
        
        ax1.set_xlabel('X (Width) [m]')
        ax1.set_ylabel('Y (Length/Height) [m]')
        ax1.set_zlabel('Z (Depth) [m]')
        ax1.view_init(elev=view_elev, azim=view_azim)
        
        # Set equal aspect ratio
        x_range = mesh.bounds[1][0] - mesh.bounds[0][0]
        y_range = mesh.bounds[1][1] - mesh.bounds[0][1]
        z_range = mesh.bounds[1][2] - mesh.bounds[0][2]
        max_range = max(x_range, y_range, z_range)
        mid_x = (mesh.bounds[1][0] + mesh.bounds[0][0]) / 2
        mid_y = (mesh.bounds[1][1] + mesh.bounds[0][1]) / 2
        mid_z = (mesh.bounds[1][2] + mesh.bounds[0][2]) / 2
        
        ax1.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
        ax1.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
        ax1.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
        
        norm_status = "Normalized" if measurements.get('normalized', False) else "Original"
        ax1.set_title(f'3D View - {norm_status}\n(elev={view_elev}°, azim={view_azim}°)', 
                     fontsize=11, fontweight='bold')
        
        # === RIGHT PLOT: PROFILE VIEW (Side view, model standing upright) ===
        # This view shows the model from the side so you can clearly see the slices
        ax2.plot_trisurf(mesh.vertices[:, 0], mesh.vertices[:, 1], 
                       mesh.vertices[:, 2], triangles=mesh.faces,
                       alpha=0.3, edgecolor='none', color='lightblue')
        
        # Draw slice planes in profile view with THICK lines for visibility
        for label, y_pos in y_levels.items():
            x_range = np.linspace(mesh.bounds[0][0], mesh.bounds[1][0], 10)
            z_range = np.linspace(mesh.bounds[0][2], mesh.bounds[1][2], 10)
            X, Z = np.meshgrid(x_range, z_range)
            Y = np.ones_like(X) * y_pos
            
            # Draw the slice plane with high opacity
            ax2.plot_surface(X, Y, Z, alpha=0.7, color=colors[label], linewidth=0)
            
            # Also draw the outline of the slice for extra clarity
            # Draw edges of the plane
            x_edge = [mesh.bounds[0][0], mesh.bounds[1][0], mesh.bounds[1][0], mesh.bounds[0][0], mesh.bounds[0][0]]
            z_edge = [mesh.bounds[0][2], mesh.bounds[0][2], mesh.bounds[1][2], mesh.bounds[1][2], mesh.bounds[0][2]]
            y_edge = [y_pos] * 5
            ax2.plot(x_edge, y_edge, z_edge, color=colors[label], linewidth=3, zorder=10)
        
        # PROFILE VIEW SETTINGS: Looking from the side (X-axis)
        # This makes the model appear "standing upright" with Y pointing up
        ax2.view_init(elev=0, azim=0)  # Pure side view
        
        ax2.set_xlabel('X (Width) [m]', fontsize=9)
        ax2.set_ylabel('Y (Length) [m]', fontsize=9, fontweight='bold')
        ax2.set_zlabel('Z (Depth) [m]', fontsize=9)
        
        ax2.set_xlim(mid_x - max_range/2, mid_x + max_range/2)
        ax2.set_ylim(mid_y - max_range/2, mid_y + max_range/2)
        ax2.set_zlim(mid_z - max_range/2, mid_z + max_range/2)
        
        ax2.set_title(f'PROFILE VIEW (Side View)\nModel Standing Upright - Slices at:', 
                     fontsize=11, fontweight='bold')
        
        # Add legend for slice positions in profile view
        legend_text = '\n'.join([f"{label}: {colors[label]}" for label in y_levels.keys()])
        ax2.text2D(0.02, 0.98, legend_text, transform=ax2.transAxes,
                  fontsize=9, verticalalignment='top',
                  bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        output_3d_path = os.path.join(viz_dir, '3d_views.png')
        plt.savefig(output_3d_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  📊 Saved 3D views: {output_3d_path}")
    except Exception as e:
        print(f"  ⚠️  Could not create 3D view: {e}")


def plot_2d_slice(ax, slice_2d, title: str, width: float):
    """
    Plot a 2D slice on the given matplotlib axis.
    """
    if slice_2d is None:
        ax.text(0.5, 0.5, 'No slice', ha='center', va='center')
        ax.set_title(title)
        return
    
    # Get vertices from the 2D slice
    vertices = slice_2d.vertices * 100.0
    
    if len(vertices) == 0:
        ax.text(0.5, 0.5, 'Empty slice', ha='center', va='center')
        ax.set_title(title)
        return
    
    # Plot the 2D cross-section
    for entity in slice_2d.entities:
        # Get points for this entity
        points = vertices[entity.points]
        # Close the loop
        points_closed = np.vstack([points, points[0]])
        ax.plot(points_closed[:, 0], points_closed[:, 1], 'b-', linewidth=2)
    
    # Plot all vertices
    ax.scatter(vertices[:, 0], vertices[:, 1], c='red', s=20, alpha=0.6, zorder=5)
    
    # Add width annotation
    if width > 0:
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.3)
        
        # Show width dimension
        x_min, x_max = vertices[:, 0].min(), vertices[:, 0].max()
        y_annotation = vertices[:, 1].min() - 0.015
        ax.annotate('', xy=(x_max, y_annotation), 
                   xytext=(x_min, y_annotation),
                   arrowprops=dict(arrowstyle='<->', color='green', lw=2.5))
     
        ax.text((x_min + x_max) / 2, y_annotation - 0.005, 
               f'{width/10:.2f} cm', ha='center', color='green', 
               fontweight='bold', fontsize=10)
    
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    ax.set_title(f'{title}\nWidth: {width/10:.2f} cm', fontsize=11, fontweight='bold')

    ax.set_xlabel('X (cm)', fontsize=10)
    ax.set_ylabel('Z (cm)', fontsize=10)
    """
    Plot a 2D slice on the given matplotlib axis.
    """
    if slice_2d is None:
        ax.text(0.5, 0.5, 'No slice', ha='center', va='center')
        ax.set_title(title)
        return
    
    # Get vertices from the 2D slice
    vertices = slice_2d.vertices * 100.0
    
    if len(vertices) == 0:
        ax.text(0.5, 0.5, 'Empty slice', ha='center', va='center')
        ax.set_title(title)
        return
    
    # Plot the 2D cross-section
    for entity in slice_2d.entities:
        # Get points for this entity
        points = vertices[entity.points]
        # Close the loop
        points_closed = np.vstack([points, points[0]])
        ax.plot(points_closed[:, 0], points_closed[:, 1], 'b-', linewidth=2)
    
    # Plot all vertices
    ax.scatter(vertices[:, 0], vertices[:, 1], c='red', s=20, alpha=0.6, zorder=5)
    
    # Add width annotation
    if width > 0:
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.3)
        
        # Show width dimension
        x_min, x_max = vertices[:, 0].min(), vertices[:, 0].max()
        y_annotation = vertices[:, 1].min() - 0.015
        ax.annotate('', xy=(x_max, y_annotation), 
                   xytext=(x_min, y_annotation),
                   arrowprops=dict(arrowstyle='<->', color='green', lw=2.5))
     
        ax.text((x_min + x_max) / 2, y_annotation - 0.005, 
               f'{width/10:.2f} cm', ha='center', color='green', 
               fontweight='bold', fontsize=10)
    
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    ax.set_title(f'{title}\nWidth: {width/10:.2f} cm', fontsize=11, fontweight='bold')

    ax.set_xlabel('X (cm)', fontsize=10)
    ax.set_ylabel('Z (cm)', fontsize=10)