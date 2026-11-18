from pathlib import Path
import hashlib, json, tarfile
root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'website-archives.json').read_text(encoding='utf-8'))
for archive in manifest['archives']:
    source = root / archive['name']
    if hashlib.sha256(source.read_bytes()).hexdigest() != archive['sha256']:
        raise RuntimeError('Website archive checksum mismatch')
    with tarfile.open(source, 'r:gz') as bundle:
        for member in bundle.getmembers():
            target = (root / member.name).resolve()
            if not target.is_relative_to(root / 'site') or not member.isfile():
                raise RuntimeError('Invalid archive entry')
        bundle.extractall(root, filter='data')
print('Unpacked verified website archives:', len(manifest['archives']))
