import pytest

from pipeline.normalize.tax_codes import is_valid_cf, is_valid_piva


# Contracting authorities from ANAC CIG data (cig_csv_2025_01), check digits verified by hand.
@pytest.mark.parametrize("code", ["81000160465", "03108560925"])
def test_valid(code):
    assert is_valid_piva(code)


@pytest.mark.parametrize(
    "code",
    [
        "81000160464",  # wrong check digit
        "3108560925",  # leading zero lost
        "031085609250",  # too long
        "0310856092A",  # letter
        "RSSMRA80A01H501U",  # 16-character personal codice fiscale
        "",
    ],
)
def test_invalid(code):
    assert not is_valid_piva(code)


def test_valid_cf():
    # Textbook example (Mario Rossi, Rome, 1 January 1980): check sum 98, 98 % 26 = 20 -> "U".
    assert is_valid_cf("RSSMRA80A01H501U")


@pytest.mark.parametrize(
    "code",
    [
        "RSSMRA80A01H501V",  # wrong check character
        "rssmra80a01h501u",  # lowercase: normalize before validating
        "RSSMRA80A01H501",  # too short
        "03108560925",  # company code
        "",
    ],
)
def test_invalid_cf(code):
    assert not is_valid_cf(code)
