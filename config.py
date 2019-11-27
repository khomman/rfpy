import os

class Config(object):
    base_dir = os.getcwd()
    if not os.path.isdir(f'{base_dir}/db'):
        os.mkdir(f'{base_dir}/db')
    
    if not os.path.isdir(f'{base_dir}/plots'):
        os.mkdir(f'{base_dir}/plots')

    if not os.path.isdir(f'{base_dir}/exports'):
        os.mkdir(f'{base_dir}/exports')

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(base_dir,'db/rftns.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DATA_ARCHIVE_STRUCTURE = "DATA/NET/STA/FILTER"

    BASE_PLOT_PATH = f"{os.path.join(base_dir, 'plots/')}"
    BASE_EXPORT_PATH = f"{os.path.join(base_dir, 'exports/')}"
