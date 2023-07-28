import wmpaws
import pandas as pd

def get_all_sites(
        broken_sites = [
        'alswiktionary', 'alswikibooks', 'alswikiquote', 'mowiki', 'mowiktionary', 
        'gpewiki', 'btmwiktionary',
        'arbcom_dewiki', 'arbcom_enwiki', 'arbcom_fiwiki', 'arbcom_nlwiki', 'auditcomwiki',
        'internalwiki', 'officewiki', 'ombudsmenwiki', 'arbcom_fiwiki', 'boardwiki', 
        'boardgovcomwiki', 'chairwiki', 'chapcomwiki', 'checkuserwiki', 'collabwiki',
        'donatewiki', 'execwiki', 'fdcwiki', 'grantswiki', 'iegcomwiki', 
        'searchcomwiki', 'spcomwiki', 'projectcomwiki', 'arbcom_cswiki', 'electcomwiki', 
        'arbcom_ruwiki', 'ilwikimedia', 'movementroleswiki', 'noboard_chapterswikimedia',
        'otrs_wikiwiki', 'stewardwiki', 'transitionteamwiki', 'ukwikimedia', 'vewikimedia',
        'wg_enwiki', 'wikimaniateamwiki', 'legalteamwiki', 'zerowiki', 'labtestwiki',
        'ecwikimedia', 'techconductwiki', 'advisorswiki', 'id_internalwikimedia', 'fixcopyrightwiki',
        'sysop_itwiki'
    ],
    return_full_table = False
):
    '''
    Collects all sites on wikimedia wikis. Returns as a list of strings.

    Takes as sites that you want to exclude. The default are sites that are known to give errors in the revisions table, which is usually because the site is not public, but the first two lines are wikis that are returning errors for unknown reasons. They usually cause an error like this: 
    `OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server on 'btmwiktionary.analytics.db.svc.wikimedia.cloud' ([Errno -2] Name or service not known)"`
    '''
    all_sites = wmpaws.run_sql(f'''
        SELECT
            *
        FROM
            sites
        LIMIT 5000
        ;
        ''', 'commonswiki')
    
    if return_full_table: 
        return(all_sites.query('site_global_key not in @broken_sites'))
    list_all_sites = [x for x in list(all_sites.site_global_key) if x not in broken_sites]
    return(list_all_sites)
