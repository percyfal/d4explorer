import numpy as np
import pandas as pd
import pyd4
import pytest
from click.testing import CliRunner

from d4explorer.d4utils import commands


def load_chromosome(d4, chrom, begin, end):
    """Load a chromosome region from a d4 file."""
    df = pd.DataFrame(
        {
            "chrom": chrom,
            "begin": np.arange(begin, end),
            "end": np.arange(begin, end) + 1,
            "value": d4.load_to_np(f"{chrom}:{begin}-{end}"),
        }
    )
    return df


@pytest.fixture
def inputs(d4file):
    s1 = d4file("s1")
    s2 = d4file("s2")
    return [s1, s2]


@pytest.fixture
def chr1(d4file):
    file = pyd4.D4File(str(d4file("s1")))
    s1 = load_chromosome(file, "chr1", 1940, 2040)
    file = pyd4.D4File(str(d4file("s2")))
    s2 = load_chromosome(file, "chr1", 1940, 2040)
    return s1, s2


@pytest.mark.parametrize("chrom,begin,end", [("chr1", 1940, 2040)])
def test_sum(inputs, tmp_path, chrom, begin, end):
    """Test d4utils sum command."""
    runner = CliRunner()
    outfile = str(tmp_path / "out.d4")
    result = runner.invoke(commands.sum, [str(x) for x in inputs] + [outfile])
    assert result.exit_code == 0
    s1 = load_chromosome(pyd4.D4File(str(inputs[0])), chrom, begin, end)
    s2 = load_chromosome(pyd4.D4File(str(inputs[1])), chrom, begin, end)
    out = load_chromosome(pyd4.D4File(outfile), chrom, begin, end)
    expected = s1["value"] + s2["value"]
    np.testing.assert_array_equal(out["value"].values, expected.values)


@pytest.mark.parametrize("chrom,begin,end", [("chr1", 1940, 2040)])
def test_sum_region(inputs, tmp_path, chrom, begin, end):
    """Test d4utils sum command with region."""
    runner = CliRunner()
    outfile = str(tmp_path / "out.d4")
    regions = tmp_path / "regions.bed"
    with open(regions, "w") as f:
        f.write(f"{chrom}\t{begin}\t{end}\n")
    print(f"d4explorer sum {' '.join([str(x) for x in inputs])} {outfile} -R {regions}")
    result = runner.invoke(
        commands.sum, [str(x) for x in inputs] + [outfile, "-R", str(regions)]
    )
    assert result.exit_code == 0
    s1 = load_chromosome(pyd4.D4File(str(inputs[0])), chrom, begin, end)
    s2 = load_chromosome(pyd4.D4File(str(inputs[1])), chrom, begin, end)
    out = load_chromosome(pyd4.D4File(outfile), chrom, begin, end)
    expected = s1["value"] + s2["value"]
    np.testing.assert_array_equal(out["value"].values, expected.values)
