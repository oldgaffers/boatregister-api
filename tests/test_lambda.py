import os
import sys
sys.path.append(os.getcwd()+'/boatregister_api')
from boatregister_api.lambda_function import lambda_handler

def test_exists():
    assert lambda_handler is not None
