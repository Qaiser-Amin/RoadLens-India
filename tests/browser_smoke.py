"""Real web-app interaction tests; not Tableau tests. Start server.py first."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1366,'height':768})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8000')
    page.wait_for_selector('[data-map-state]')
    assert page.locator('[data-map-state]').count()==36
    assert page.locator('[data-kpi="fatalities"] strong').inner_text()=='1,72,890'
    page.select_option('#year','2022')
    assert page.locator('[data-kpi="fatalities"] strong').inner_text()=='1,68,491'
    # Keyboard activation exercises the same handler as state-map clicking.
    page.locator('[data-map-state="Kerala"]').focus()
    page.keyboard.press('Enter')
    assert page.locator('[data-kpi="fatalities"] strong').inner_text()=='4,317'
    page.click('[data-tab="twowheelers"]')
    assert page.locator('[data-kpi="fatalities"] strong').inner_text()=='2,424'
    assert page.locator('[data-kpi="severity"] strong').inner_text()=='Unavailable'
    page.select_option('#metric','accidents')
    assert 'unavailable' in page.locator('#dashboard').inner_text().lower()
    page.select_option('#year','2020')
    assert page.locator('[data-kpi="fatalities"] strong').inner_text()=='Unavailable'
    page.click('#reset')
    assert page.locator('[data-kpi="fatalities"] strong').inner_text()=='1,72,890'
    assert page.locator('nav button.active').get_attribute('data-tab')=='overview'
    page.select_option('#topN','5')
    assert page.locator('.barrow').count()==5
    page.select_option('#topN','15')
    assert page.locator('.barrow').count()==15
    page.select_option('#metric','accidents')
    assert '67,213' in page.locator('.barrow').first.inner_text()
    page.select_option('#year','all')
    assert page.locator('.trend circle').count()==4
    page.click('[data-tab="risks"]')
    page.fill('#threshold','20')
    page.locator('#threshold').press('Tab')
    assert page.locator('#threshold').input_value()=='20'
    assert page.locator('.risk-table tbody tr').count()==15
    page.click('#reset')
    page.click('#stateSummary')
    page.locator('[data-state-check][value="Kerala"]').check()
    page.locator('[data-state-check][value="Tamil Nadu"]').check()
    page.click('#stateSummary')
    assert page.locator('[data-kpi="fatalities"] strong').inner_text()=='22,427'
    page.click('[data-tab="twowheelers"]')
    page.select_option('#year','all')
    assert page.locator('.trend-legend span').count()==2
    page.click('#sourcesBtn')
    assert page.locator('#sourceDialog').is_visible()
    page.click('#closeSources')
    page.click('#reset')
    page.screenshot(path='/tmp/roadlens-desktop.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path='/tmp/roadlens-mobile.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.wait_for_timeout(200)
    page.click('[data-tab="twowheelers"]')
    assert page.locator('[data-kpi="severity"] strong').inner_text()=='Unavailable'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.click('[data-tab="risks"]')
    page.fill('#threshold','1000');page.locator('#threshold').press('Tab')
    assert not page.locator('.risk-table tbody td:nth-child(5)').filter(has_text='In set').count()
    page.fill('#threshold','0');page.locator('#threshold').press('Tab')
    assert page.locator('.risk-table tbody td:nth-child(5)').filter(has_text='In set').count()>0
    page.click('#reset')
    with page.expect_download() as item:
        page.click('#download')
    download=item.value
    assert download.suggested_filename=='state_totals.csv'
    assert len(open(download.path()).read().strip().splitlines())==145
    assert not errors,errors
    browser.close()
    print('PASS: year, state map, navigation, missing data, metric, Top N, historical trend, risk threshold, multi-state comparison, reset, methodology, desktop/mobile overflow; no JS errors.')
