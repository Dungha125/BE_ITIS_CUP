# Export all from schemas.py
# Import directly from the parent schemas.py file
import sys
import os
import importlib.util

# Get the path to schemas.py (parent directory)
parent_dir = os.path.dirname(os.path.dirname(__file__))
schemas_py_path = os.path.join(parent_dir, 'schemas.py')

# Load schemas.py as a module
spec = importlib.util.spec_from_file_location("schemas_py_module", schemas_py_path)
schemas_py_module = importlib.util.module_from_spec(spec)
sys.modules["schemas_py_module"] = schemas_py_module
spec.loader.exec_module(schemas_py_module)

# Export classes from schemas.py
TeamRegisterRequest = schemas_py_module.TeamRegisterRequest
CreatePaymentRequest = schemas_py_module.CreatePaymentRequest
TeamResponse = schemas_py_module.TeamResponse
RegisterTeamResponse = schemas_py_module.RegisterTeamResponse
CreatePaymentResponse = schemas_py_module.CreatePaymentResponse
TeamsListResponse = schemas_py_module.TeamsListResponse
MomoIpnRequest = schemas_py_module.MomoIpnRequest
# Note: MomoIpnResponse does not exist in schemas.py, only MomoIpnRequest

# Export auth schemas from auth.py in this package
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    RegisterResponse,
    LoginResponse,
)

