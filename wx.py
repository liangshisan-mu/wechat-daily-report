#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""兼容入口：python wx.py <command> 等价于 python -m wxread.wx <command>。"""

from wxread.wx import main

if __name__ == "__main__":
    main()
