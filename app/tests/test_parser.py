# tests/test_parser.py
import pytest
import pandas as pd
from app.bankstatements.santander import SantanderParser


class TestSantanderParser:
    def setup_method(self):
        self.parser = SantanderParser()

    def test_parse_valid_data(self):
        # Datos de prueba
        data = {
            'MONTO': ['100.000', '-50.000'],
            'DESCRIPCIÓN MOVIMIENTO': ['Depósito', 'Compra'],
            'FECHA': ['01/01/2024', '02/01/2024'],
            'CARGO/ABONO': ['A', 'C']
        }
        df = pd.DataFrame(data)

        result = self.parser.parse(df)

        assert len(result) == 2
        assert 'Fecha' in result.columns
        assert 'Descripción' in result.columns
        assert 'Monto' in result.columns
        assert result.iloc[0]['Monto'] == 100000
        assert result.iloc[1]['Monto'] == -50000

    def test_parse_invalid_data(self):
        # Datos inválidos
        df = pd.DataFrame({'col1': ['data']})

        with pytest.raises(ValueError):
            self.parser.parse(df)