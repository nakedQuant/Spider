# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import pandas as pd, re
from collections import defaultdict


# import numpy as np, requests, time
# def _parse_url(url, encoding='gbk', bs=True):
#     """
#     :param url: url_path和你
#     :param encoding: utf-8 or gbk
#     :param bs: bool
#     :param proxy: proxies = {"http": "http://10.10.1.10:3128", "https": "http://10.10.1.10:1080"} ,list
#     :return:
#     """
#     header = {'User-Agent': UserAgent[np.random.randint(0, len(UserAgent)-1)]}
#     # proxy = {'http': ProxyIp[np.random.randint(0, len(ProxyIp) - 1)]}
#     proxy = None
#     # delay in case of httpError
#     time.sleep(np.random.random(1)[0])
#     if proxy:
#         req = requests.get(url, headers=header, proxies=proxy, timeout=3)
#     else:
#         req = requests.get(url, headers=header, timeout=3)
#     req.encoding = encoding
#     if bs:
#         data = BeautifulSoup(req.text, features='lxml')
#     else:
#         data = req.text
#     return data

# from toolz import valmap
#
# def unpack_df_to_component_dict(stack, col=None):
#     """Returns the set of known tables in the adjustments file in DataFrame
#     form.
#
#     Parameters
#     ----------
#     stack : pd.DataFrame , stack
#     col : column used to set index
#     Returns
#     -------
#     dfs : dict{str->DataFrame}
#         Dictionary which maps sid name to the corresponding DataFrame
#         version of the table, where all date columns have been coerced back
#         from int to datetime.
#     """
#     unpack = defaultdict(pd.DataFrame)
#     for index, raw in stack.iterrows():
#         unpack[index] = unpack[index].append(raw, ignore_index=True)
#     # set trade_dt to index
#     _unpack = valmap(lambda x: x.set_index(col), unpack) if col else unpack
#     return _unpack


def parse_content_from_header(header):
    cols = [t.get_text() for t in header.findAll('td', {'width': re.compile('[0-9]+')})]
    raw = [t.get_text() for t in header.findAll('td')]
    # xa0为空格
    raw = [''.join(item.split()) for item in raw]
    # 去除格式
    raw = [re.sub('·', '', item) for item in raw]
    # 调整字段
    raw = [re.sub('\(历史记录\)', '', item) for item in raw]
    raw = [item.replace('万股', '') for item in raw]
    # 结构处理
    num = int(len(raw) / len(cols))
    text = {}
    for count in range(len(cols)):
        idx = count * num
        mid = raw[idx:idx + num]
        text.update({mid[0]: mid[1:]})
    contents = pd.DataFrame.from_dict(text)
    return contents


def transfer_to_timestamp(dt):
    if isinstance(dt, float):
        timestamps = dt
    elif isinstance(dt, pd.Timestamp):
        timestamps = dt.timestamp()
    else:
        try:
            stamp = pd.Timestamp(dt)
        except Exception as e:
            raise TypeError('cannot tranform %r to timestamp due to %s' % (dt, e))
        timestamps = stamp.timestamp()
    return timestamps


def unstack_value(result, assets, missing_value):
    """
    Called with a column of the result of a pipe. This needs to put
    the data into a format that can be used in a workspace to continue
    doing computations.

    Parameters
    ----------
    result : pd.Series
        A multiindexed series with (dates, assets) whose values are the
        results of running this pipe term over the dates.
    assets : pd.Index
        All of the assets being requested. This allows us to correctly
        shape the workspace value.

    Returns
    -------
    workspace_value : array-like
        An array like value that the engine can consume.
    """
    return result.unstack().fillna(missing_value).reindex(
        columns=assets,
        fill_value=missing_value,
    ).values
