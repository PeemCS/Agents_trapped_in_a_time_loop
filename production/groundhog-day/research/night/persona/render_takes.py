"""Write a readable edit log from finished model output, independent of model libraries."""
from pathlib import Path
from analyze import OUT, load

HOME=Path(__file__).resolve().parent
ACTORS=[
    ('Neutral base',OUT/'base_neutral.jsonl',OUT/'shoot-base_neutral.jsonl'),
    ('Base with explicit persona cue',OUT/'base_cued.jsonl',OUT/'shoot-base_cued.jsonl'),
    ('First adapter with neutral prompt',OUT/'adapter_neutral.jsonl',OUT/'shoot-adapter_neutral.jsonl'),
    ('Repaired adapter with neutral prompt',OUT/'v2/native/adapter_neutral.jsonl',OUT/'v2/shoot-adapter_neutral.jsonl'),
]

def block(txt):
    return '\n'.join('> '+line for line in txt.strip().splitlines()) if txt.strip() else '*No final text was emitted.*'

def main():
    doc=['# Four readings of the same film', '',
         'All quoted passages below are the complete visible final text for the shot. The raw call files also preserve the emitted thinking text and token IDs. The editor executes a choice only after a valid final answer. The actor’s line can contradict that choice.','',
         '## The Wet Print','',
         'Phil can take a paid weather audition or carry the sound tin for Rita’s Pittsburgh screening. She and Phil once salvaged her mother’s recorded interview. Their later options change with the physical choice. At six, the tin and Tuesday’s calendar return.','']
    for name,_,path in ACTORS:
        rows=load(path)
        doc.extend([f'### {name}',''])
        for r in rows:
            doc.extend([f"**Beat {r['beat']}**",'',block(r['final']),'',
                        (r['physical_outcome'] or 'The engine stopped here because the actor supplied no executable final decision.'),''])
        doc.extend(['[Raw take]('+str(path.relative_to(HOME))+')',''])
    doc.extend(['## Two open dialogue shots',''])
    for key,title in [('projectionist','The projectionist'),('organ','The organ landing')]:
        doc.extend([f'### {title}',''])
        first=next(r for r in load(ACTORS[0][1]) if r['id']==key)
        doc.extend([block(first['messages'][1]['content']),''])
        for actor,path,_ in ACTORS:
            row=next(r for r in load(path) if r['id']==key)
            doc.extend([f'**{actor}**','',block(row['final']),''])
    (HOME/'story-takes.md').write_text('\n'.join(doc).rstrip()+'\n')
if __name__=='__main__':
    main()
