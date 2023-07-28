import wmpaws
import pandas as pd

def get_actor_id(
    wiki = "commonswiki",
    userlist = ["한솔임", "후니훈"],
    limit=100
):
    '''
    Collects all actor IDs for a list of users.
    Input: 
    * wiki
    * userlist: list of strings. May give problems with some special characters.
    * limit: default is low for testing purposes. Set sufficiently high. 
    Returns: a dataframe
    '''
    userlist_str = ','.join([f'{repr(s)}' for s in userlist])
    df_out = wmpaws.run_sql(f'''
    SELECT
        actor.actor_name AS username,
        actor.actor_id AS actor_id
    FROM
        actor
    WHERE
        actor.actor_name IN ({userlist_str})
    LIMIT {limit}
    ;
    ''', wiki)
    return(df_out)

def get_actor_id_all_wikis(list_all_sites):
    '''
    Loop function to collect the actor IDs for a set of usernames 
    across a list of wikis. 
    
    Input:
    * list_all_sites: a list of all wikis you want to check
    * df_users: pandas dataframe with at least a column 'uploader' with usernames that you want to check for

    Returns: pandas dataframe with one row per user-wiki combination that the user exists on. If username is not found on the wiki, it does not return a row.
    '''
    list_ids = []
    for wiki in list_all_sites:
        actor_id_temp = get_actor_id(
            wiki = wiki,
            userlist = df_users['uploader'],
            limit = len(df_users)
        )
        actor_id_temp['wiki'] = wiki
        list_ids += [actor_id_temp]
    df_list_ids = pd.concat(list_ids)
    return(df_list_ids)