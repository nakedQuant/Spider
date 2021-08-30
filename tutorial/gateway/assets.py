# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""


class Asset(object):
    """
    Base class for entities that can be owned by a trading algorithm.

    Attributes
    ----------
    sid : str
        Persistent unique identifier assigned to the asset.

    缓存实例 --- 持久化

    """


class Asset(object):
    """
    Base class for entities that can be owned by a trading algorithm.

    Attributes
    ----------
    sid : str
        Persistent unique identifier assigned to the asset.
    """
    __slots__ = ['sid', '_tag']

    def __init__(self, sid):
        self.sid = sid
        self._tag = None

    def _initialize_basics_mappings(self):
        table = metadata.tables['asset_router']
        ins = select([table.c.asset_type, table.c.asset_name, table.c.first_traded,
                      table.c.last_traded, table.c.country_code, table.c.exchange])
        ins = ins.where(table.c.sid == self.sid)
        rp = engine.execute(ins)
        basics = pd.DataFrame(rp.fetchall(), columns=['asset_type', 'asset_name', 'first_traded',
                                                      'last_traded', 'country_code', 'exchange'])
        for k, v in basics.iloc[0, :].items():
            self.__setattr__(k, v)

    def _implement_supplementary(self):
        raise NotImplementedError()

    @property
    def tick_size(self):
        return 100

    @property
    def increment(self):
        # increment True means increment by tick_size
        return True

    @property
    def inter_day(self):
        # 日内交易日
        return False

    @property
    def tag(self):
        return self._tag

    def bid_mechanism(self):
        """
            科创板 : 在临时停牌阶段，投资者可以继续申报也可以撤销申报，并且申报价格不受2%的报价限制。
            复牌时，对已经接受的申报实行集合竞价撮合交易，申报价格最小变动单位为0.01
            超出价位 --- 申报单为废单
            创业板也有竞价机制但是超出价格的单子缓存在后台，当价格触及是成交
        """
        return False

    def source_id(self, tg):
        self._tag = tg
        return self

    def restricted_change(self, dt):
        """
        the limit pctchange of asset on dt
        :param dt: str
        :return: float
        """
        raise NotImplementedError()

    def _is_active(self, session_label):
        """
        Returns whether the asset is alive at the given dt and not suspend on the given dt

        Parameters
        ----------
        session_label: pd.Timestamp
            The desired session label to check. (midnight UTC)

        Returns
        -------
        boolean: whether the asset is alive at the given dt.
        """
        if self.last_traded :
            active = self.first_traded <= session_label <= self.last_traded
        else:
            active = self.first_traded <= session_label
        return active

    def is_active(self, session_label):
        active = self._is_active(session_label)
        return active

    def can_be_traded(self, dt):
        close = portal.get_spot_value(dt, self, 'daily', ['close'])
        traded = False if close.empty else True
        return traded

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, self.sid)

    def __reduce__(self):
        """
        Function used by pickle to determine how to serialize/deserialize this
        class.  Should return a tuple whose first element is self.__class__,
        and whose second element is a tuple of all the attributes that should
        be serialized/deserialized during pickling.
        """
        return (self.__class__, (self.sid,
                                 self.asset_name,
                                 self.asset_type,
                                 self.exchange,
                                 self.first_traded,
                                 self.last_traded,
                                 self.tick_size,
                                 ))

    def to_dict(self):
        """Convert to a python dict containing all attributes of the asset.

        This is often useful for debugging.

        Returns
        -------
        as_dict : dict
        """
        return {
            'sid': self.sid,
            'asset_name': self.asset_name,
            'first_traded': self.first_traded,
            'last_traded': self.last_traded,
            'exchange': self.exchange,
            'tick_size': self.tick_size,
        }


class Equity(Asset):
    """
    Asset subclass representing partial ownership of a company, trust, or
    partnership.
    """

    def __init__(self, sid):
        super(Equity, self).__init__(sid)
        super()._initialize_basics_mappings()
        self._implement_supplementary()

    def _implement_supplementary(self):
        tbl = metadata.tables['equity_basics']
        ins = sa.select([tbl.c.dual_sid,
                         tbl.c.broker,
                         tbl.c.district,
                         tbl.c.initial_price]).where(tbl.c.sid == self.sid)
        rp = engine.execute(ins)
        raw = pd.DataFrame(rp.fetchall(), columns=['dual',
                                                   'broker',
                                                   'district',
                                                   'initial_price'])
        for k, v in raw.iloc[0, :].to_dict().items():
            self.__setattr__(k, v)

    @property
    def tick_size(self):
        _tick_size = 200 if self.sid.startswith('688') else 100
        return _tick_size

    @property
    def increment(self):
        augment = False if self.sid.startswith('688') else True
        return augment

    def restricted_change(self, dt):
        """
            科创板股票上市后的前5个交易日不设涨跌幅限制，从第六个交易日开始设置20%涨跌幅限制
            创业版2020-08-24开始实行的新规: 上市前五个交易日不设立涨跌停限制之后20% （原来首日44%， 10%）
        """
        assert dt >= self.first_traded, 'dt must be after first_traded'
        end_dt = calendar.dt_window_size(dt, RestrictedWindow)
        if self.first_traded < '2020-08-24':
            # print('apply to old cyb regulation')
            if self.first_traded == dt:
                pct = np.inf if self.sid.startswith('688') else 0.44
            elif self.first_traded >= end_dt:
                pct = np.inf if self.sid.startswith('688') else 0.1
            else:
                pct = 0.2 if self.sid.startswith('688') else 0.1
        else:
            # print('new regulation of cyb')
            if self.first_traded == dt:
                pct = np.inf if self.sid.startswith('688') else \
                    np.inf if self.sid.startswith('3') else 0.44
            elif self.first_traded >= end_dt:
                pct = np.inf if self.sid.startswith('688') or self.sid.startswith('3') else \
                    (0.2 if self.sid.startswith('3') else 0.1)
            else:
                pct = 0.2 if self.sid.startswith('688') or self.sid.startswith('3') else 0.1
        return pct

    @property
    def bid_mechanism(self):
        bid_mechanism = True if self.sid.startswith('688') else False
        return bid_mechanism

    def is_specialized(self, dt):
        """
            equity is special treatment on dt
        :param dt: str e.g. %Y-%m-%d
        :return: bool
        """
        raise NotImplementedError


class Convertible(Asset):
    """
       我国《上市公司证券发行管理办法》规定，可转换公司债券的期限最短为1年，最长为6年，自发行结束之日起6个月方可转换为公司股票
       回售条款 --- 最后两年
       1.强制赎回 --- 股票在任何连续三十个交易日中至少十五个交易日的收盘价格不低于当期转股价格的125%(含 125%)
       2.回售 --- 公司股票在最后两个计息年度任何连续三十个交易日的收盘价格低于当期转股价格的70%时
       3. first_traded --- 可转摘转股日期
       限制条件:
       1.可转换公司债券流通面bai值少于3000万元时，交易所立即公告并在三个交易日后停止交易
       2.可转换公司债券转换期结束前的10个交易日停止交易
       3.中国证监会和交易所认为必须停止交易
    """

    def __init__(self, bond_id):
        super(Convertible, self).__init__(bond_id)
        super()._initialize_basics_mappings()
        self._implement_supplementary()

    def _implement_supplementary(self):
        tbl = metadata.tables['convertible_basics']
        ins = sa.select([tbl.c.swap_code,
                         tbl.c.put_price,
                         tbl.c.redeem_price,
                         tbl.c.convert_price,
                         tbl.c.convert_dt,
                         tbl.c.put_convert_price,
                         tbl.c.guarantor]).\
            where(tbl.c.sid == self.sid)
        rp = engine.execute(ins)
        df = pd.DataFrame(rp.fetchall(), columns=['swap_code',
                                                  'put_price',
                                                  'redeem_price',
                                                  'convert_price',
                                                  'convert_dt',
                                                  'put_convert_price',
                                                  'guarantor'])

        for k, v in df.iloc[0, :].to_dict().items():
            self.__setattr__(k, v)

    @property
    def inter_day(self):
        return True

    def restricted_change(self, dt):
        return None


class Fund(Asset):
    """
    ETF --- exchange trade fund
    目前不是所有的ETF都是t+0的，只有跨境ETF、债券ETF、黄金ETF、货币ETF实行的是t+0，境内A股ETF暂不支持t+0
    10%
    """

    def __init__(self, fund_id):
        super(Fund, self).__init__(fund_id)
        super()._initialize_basics_mappings()

    def restricted_change(self, dt):
        # fund 以1或者5开头 --- 5（SH） 1（SZ）
        raise  NotImplementedError('创业板ETF或者科创板ETF为20%， 其他为10% 具体分析')

