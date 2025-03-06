import os

def get_data_path() -> list[str]:
    """获取数据集完整路径"""
    data_folder_path = './project/sample_data' # "" 
    files = os.listdir(data_folder_path)
    full_paths = [os.path.abspath(os.path.join(data_folder_path, file)) for file in files]
    return full_paths


if __name__ == "__main__":
    print(get_data_path())