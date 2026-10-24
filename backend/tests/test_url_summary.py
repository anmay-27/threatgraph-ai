from app.services.url_summary import summarize_url


def test_summary_uses_submitted_page_not_embedded_redirects():
    report={'assets':[{'id':'root','type':'url','url':'https://example.com/'}],
        'graph':{'edges':[{'source':'root','target':'page','relation':'contains'}]},
        'evidence':[
            {'id':'p','asset_id':'page','label':'page_metadata','metadata':{'title':'Form','data_collection':{'forms':[{'field_types':[],'displayed_field_types':['email'],'fields':[{'disabled':True}]}]}}},
            {'id':'redirect','asset_id':'other','label':'redirect_chain','metadata':{'chain':[['https://asset.example/','https://w3.org/']]}}
        ],'checks':[{'id':'reputation','status':'not_checked','summary':'Disabled by privacy mode'}]}
    summary=summarize_url('https://example.com/',report)
    assert summary['final_host']=='example.com'
    assert summary['requested_data']==['email']
    assert summary['findings']==[]
    assert summary['gaps']==['Disabled by privacy mode']
    assert any('disabled' in x for x in summary['observations'])
    assert 'safety certificate' in summary['meaning']
