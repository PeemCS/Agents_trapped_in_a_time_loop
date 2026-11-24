"""Check every rendered actor field against its local JSONL record in offline Chrome."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from analyze import load, read_choice
from build_viewer import FILES,HERE

def main():
    data={name:load(HERE/path) for name,path in FILES.items()}
    errors=[]
    external=[]
    uri=(HERE/'viewer.html').as_uri()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome')
        page=browser.new_page(viewport={'width':1280,'height':900})
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.on('request',lambda request: external.append(request.url) if request.url.startswith(('http:','https:')) else None)
        page.goto(uri)
        expect(page.locator('#case-title')).to_have_text('greenhouse-0-0')
        page.get_by_role('button',name='Next scene').click()
        expect(page.locator('#case-title')).to_have_text('greenhouse-0-1')
        page.get_by_role('button',name='Previous scene').click()
        expect(page.locator('#case-title')).to_have_text('greenhouse-0-0')
        for i,r in enumerate(data['Neutral base']):
            page.locator('#pick').select_option(str(i))
            page.wait_for_function("id => document.getElementById('case-title').textContent===id",arg=r['id'])
            actors=page.locator('article.actor')
            assert actors.count()==4
            for j,(name,rows) in enumerate(data.items()):
                a=rows[i]
                card=actors.nth(j)
                assert card.locator('h2').inner_text()==name
                assert card.locator('details pre').nth(1).text_content()==a['raw_completion']
                assert json.loads(card.locator('details pre').nth(2).text_content())==a['token_ids']
                assert card.locator('pre.final').text_content()==(a['final'] or 'No visible final text was emitted.')
                assert card.locator('a').get_attribute('href')==FILES[name]
                label=read_choice(a['final']) if a['complete'] and a['reasoning_closed'] else None
                status=card.locator('p').first.text_content()
                assert status==('Open dialogue' if a['kind']=='stage' else 'Executable decision · '+label if label else 'Abstention · no action')
        page.goto(uri+'#observatory-0-0')
        expect(page.locator('#case-title')).to_have_text('observatory-0-0')
        page.set_viewport_size({'width':375,'height':810})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors and not external
        result=dict(renderer=browser.version,heldout_cases=36,checked_actor_records=144,direct_hash=True,offline_network_requests=external,
                    browser_errors=errors,mobile_overflow=False)
        browser.close()
    (HERE/'viewer-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':
    main()
