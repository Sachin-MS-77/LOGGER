import io,tarfile
from scripts.fetch_datasets import extract
from scripts.measure_coverage import measure
import pytest

def test_archive_traversal_is_rejected(tmp_path):
    archive=tmp_path/'evil.tar.gz'
    with tarfile.open(archive,'w:gz') as f:
        m=tarfile.TarInfo('../outside');m.size=1;f.addfile(m,io.BytesIO(b'x'))
    with pytest.raises(ValueError,match='unsafe'):extract(archive,tmp_path/'safe','tar')
    assert not (tmp_path/'outside').exists()

def test_coverage_accounts_for_unknown_failed_and_metadata(tmp_path):
    p=tmp_path/'records.log';p.write_bytes(b'#header\n'+b'unknown words\n'+b'\xff\n')
    result=measure(p)
    assert result['physical_lines']==3 and result['metadata_lines']==1
    assert result['records']==2 and result['discovery']==1 and result['failed']==1
