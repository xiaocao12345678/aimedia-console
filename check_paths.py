import os, sys
sys.path.insert(0, ".")
from core.paths import app_dir, resource_dir, asset_path, output_dir, log_dir
print("app_dir     ", app_dir())
print("resource_dir", resource_dir())
print("asset       ", asset_path("combo_arrow.png"))
print("exists      ", os.path.exists(asset_path("combo_arrow.png")))
print("output      ", output_dir())
print("log         ", log_dir())
