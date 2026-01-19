# 贵州电信iptv逆向
需要自行抓包获取认证信息以及机顶盒相关参数:
        self.config = {
            'base_url': '认证服务器ip:port,自行抓包',
            'user_id': 'itv账号',
            'authenticator': '抓包获取',
        }

        # 硬件参数
        self.hardware_params = {
            'stbinfo': '抓包获取',
            'stbtype': '抓包获取',
            'drmsupplier': '0',
            'prmid': '',
            'easip': '抓包获取',
            'networkid': '1',
            'stbmac': '机顶盒MAC'
        }
        
Python实现模拟贵州电信iptv机顶盒

0.第一次使用需要先行通过运营商机顶盒抓包一次,通过wireshark分析http相关认证参数与机顶盒硬件参数

1.使用Python3.13环境运行iptv.py脚本可实现一键获取贵州电信iptv最新频道列表

2.使用To_M3U.py处理第一步产生的final_frameset_builder.html,即可得到同时包含组播,fcc,单播回放地址的m3u文件

3.搭建rtp2httpd实现组播转单播以及fcc快速换台支持,也可以考虑直接通过单播观看直播

4.修改m3u中的实际rtp2httpd代理地址,最后enjoy it!
