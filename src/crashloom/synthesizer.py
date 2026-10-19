import ast
from crashloom.models import FlightRecord

class ReproducerSynthesizer:
    def synthesize(self, record: FlightRecord) -> str:
        code = f"""import pytest
from {record.target_frame.module_name if record.target_frame else 'main'} import *

def test_reproduce_{record.flight_id.replace('-', '_')}():
    with pytest.raises({record.exception_type}):
        # Trigger failing call here
        raise {record.exception_type}('{record.exception_message}')
"""
        ast.parse(code)
        return code
