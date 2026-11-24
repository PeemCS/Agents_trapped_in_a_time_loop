"""Blind offline pair rater. Works with just a packet and the Python standard library."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


def checkpoint(path, obj):
    with tempfile.NamedTemporaryFile('w', dir=path.parent, encoding='utf-8', delete=False) as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        tmp = handle.name
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rater', required=True, help='Your name or an agreed pseudonym')
    parser.add_argument('--type', choices=('human','agent'), required=True)
    args = parser.parse_args()
    if args.packet.resolve() == args.out.resolve():
        parser.error('Choose a separate output file for judgments.')
    data = json.loads(args.packet.read_text())
    signature = hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    rows = data['comparisons']
    output = {'packet_sha256':signature, 'rater_type':args.type,'rater':args.rater,
              'ratings':{row['id']:'' for row in rows}}
    if args.out.exists():
        prior = json.loads(args.out.read_text())
        if any(prior.get(k)!=output[k] for k in ('packet_sha256','rater_type','rater')) or prior['ratings'].keys()!=output['ratings'].keys():
            parser.error('The existing output belongs to a different packet or rater.')
        if any(v not in ('','A','B','tie','skip') for v in prior['ratings'].values()):
            parser.error('The existing output contains unrecognized answers.')
        output = prior
    print(data['instructions'], '\n')
    for i,row in enumerate(rows,1):
        uid = row['id']
        if output['ratings'][uid]:
            continue
        print(f'[{i}/{len(rows)}] {row["situation"]}\n\nA   {row["A"]}\n\nB   {row["B"]}\n')
        while True:
            try:
                answer = input('A, B, tie, skip, or quit and resume later > ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = 'quit'
            if answer == 'quit':
                print('Session closed. Completed judgments were saved.')
                return
            if answer in ('a','b','tie','skip'):
                output['ratings'][uid] = answer.upper() if answer in ('a','b') else answer
                checkpoint(args.out, output)
                break
    print(f'{len(rows)} judgments saved in {args.out}.')


if __name__ == '__main__':
    main()
