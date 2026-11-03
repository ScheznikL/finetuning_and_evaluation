import json
import os
import subprocess
import trimesh
import numpy as np

base_dir='./evaluation_test/meshes'

def check_watertightness_blender(mesh_path, blender_bin_path):
    """
    Calls Blender to calculate BER and returns the formatted dictionary.
    """
    script_path = r'D:\pyProj\hellocd\evaluation_test\testing_Hunuyuan3d\calc_ber.py'  # Ensure this path is correct relative to execution

    # Validate inputs
    if not os.path.exists(mesh_path):
        return {"error": "File not found"}
    if not os.path.exists(blender_bin_path):
        print(f"CRITICAL ERROR: Blender not found at: {blender_bin_path}")
        exit(1)
    
    # 1. Run Blender as a subprocess
    cmd = [
        blender_bin_path,
        '-b',                       # Background mode
        '-P', script_path,          # Run python script
        '--', 
        '--object', # Pass arguments to script
        mesh_path
    ]
#  ' "$BLENDER_PATH" -b -P render/render.py -- \
#        --object "$INPUT_FILE" \
#        --output_folder "$RENDER_DIR" \
#        --geo_mode --resolution 512 --view 12'
    try:
        # Run command and capture stdout
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            check=True
        )

        # 2. Parse the Output
        # We look for the line starting with "JSON_DATA:"
        raw_data = None
        for line in result.stdout.splitlines():
            if line.startswith("JSON_DATA:"):
                json_str = line.replace("JSON_DATA:", "").strip()
                raw_data = json.loads(json_str)
                break
        
        if not raw_data or "error" in raw_data:
            print(f"Blender Error: {raw_data.get('error') if raw_data else 'No data returned'}")
            return None

        # 3. Calculate Derived Metrics
        total_edges = raw_data['total']
        boundary_edges_count = raw_data['boundary']
        
        # Calculate BER (Avoid division by zero)
        ber = (boundary_edges_count / total_edges) if total_edges > 0 else 0.0
        is_watertight = (boundary_edges_count == 0) and (total_edges > 0)


        # 4. Return the EXACT dictionary structure requested
        return {
            "file": mesh_path,
            "is_watertight": is_watertight,
            "total_edges_Em": total_edges,
            "boundary_edges_E_partial_M": boundary_edges_count,
            "BER": ber,
            "status": "Holes detected" if ber > 0 else "Perfectly Watertight"
        }

    except subprocess.CalledProcessError as e:
        print(f"Blender crashed: {e.stderr}")
        return None
   
   
def calculate_ber(mesh_path):
    """
    Обчислює Boundary Edge Ratio (BER) для заданої 3D-сітки.
    
    Аргументи:
        mesh_path (str): Шлях до файлу моделі (наприклад, .stl або .obj)
        
    Повертає:
        dict: Словник зі статистикою та значенням BER
    """

    mesh = trimesh.load(mesh_path, force='mesh')
    
    total_edges = len(mesh.edges_unique)
    
    # edges_sorted - це ребра, відсортовані так, що (1,0) стає (0,1) для порівняння.
    edges = mesh.edges_sorted
    # count - скільки разів кожне ребро зустрічається в списку
    unique, inverse, counts = np.unique(edges, return_inverse=True, return_counts=True, axis=0)
    
    # Граничні ребра - це ті, що зустрічаються лише 1 раз (з'єднані з 1 гранню)
    boundary_edges_count = np.sum(counts == 1)
    
    # Альтернативний метод через вбудовану властивість trimesh (для перевірки):
    #boundary_edges_count = len(mesh.edges_unique) - len(mesh.edges_unique_length) #*при певних умовах*
    # Але надійніше використовувати numpy count == 1, як вище, або mesh.grouping
    
    # 4. Обчислення BER
    if total_edges == 0:
        return None # Уникнення ділення на нуль для пустих мешів
        
    ber = boundary_edges_count / total_edges
    
    # 5. Перевірка на герметичність (Watertightness) засобами бібліотеки
    is_watertight = mesh.is_watertight
    
    return {
        "file": mesh_path,
        "is_watertight": is_watertight,
        "total_edges_Em": total_edges,
        "boundary_edges_E_partial_M": boundary_edges_count,
        "BER": ber,
        "status": "Holes detected" if ber > 0 else "Perfectly Watertight"
    }


if __name__ == "__main__":
    # Створіть тестовий об'єкт (наприклад, куб)
    mesh = trimesh.creation.box()
    # Зробимо його "негерметичним", видаливши одну грань
    mesh.faces = mesh.faces[:-1] 
    # Збережемо для тесту
    mesh.export("test_broken_cube.obj")
    
    # Оцінка
    result = calculate_ber("test_broken_cube.obj")
    
    print(f"--- Результат оцінки BER ---")
    print(f"Об'єкт: {result['file']}")
    print(f"Загальна кількість ребер (EM): {result['total_edges_Em']}")
    print(f"Граничні ребра (E∂M): {result['boundary_edges_E_partial_M']}")
    print(f"BER (Boundary Edge Ratio): {result['BER']:.5f}")
    print(f"Висновок: {result['status']}")
    for dir in sorted(os.listdir(base_dir)):
        pt=os.path.join(base_dir,dir)
        if not os.path.isdir(pt) or os.path.basename(dir) != to_include:
            continue

        for sub_dir in sorted(os.listdir(pt)):
            sub_pt=os.path.join(pt,sub_dir)
            if not os.path.isdir(sub_pt) or os.path.basename(sub_dir) == "test" or os.path.basename(sub_dir) == "mantion":
                continue
            meshes = []
            cnt_sub_dir+=1
            for file in sorted(os.listdir(sub_pt)):
                #filename=file.split(ext_name)[0]
                filename = file[: -4] #4 is len of ext
                meshes.append(os.path.join(sub_pt,file))

            if len(meshes)>0:
                #process_one_with_vertices(meshes)
                process_one_from_surface(meshes)
            else:
                print("[WARN] Meshes empty")
            print(f"cnt sub_dir:{cnt_sub_dir}")