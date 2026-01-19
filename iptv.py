#!/usr/bin/env python3
"""
贵州电信IPTV - 简化版（只获取HTML）
获取认证后的最终HTML页面，供后续分析使用
"""

import requests
import re
import sys
import time
import html
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse


class GZITVHTMLFetcher:
    def __init__(self):
        # 基础配置
        self.config = {
            'base_url': 'http://10.255.12.10:18121',
            'user_id': '08570018514933@iptv',
            'authenticator': '5CDFF3483CC112F01CABF4BEA4B54F9CF1E74D8C3AA5F7A50C7A961F75B6637EBE79C6C1A73658D92E4AF0CF0F7BA6181FF73262E095B3C3147FEE53525432B158C934B5BF3E1CD359E498C956A078FBF8B261C1A97A93DE9387D1C50C0767E6C655F1FC75E2BFD702164F1CBC82BFB5456FD0F248EB6366A401F2D749BAEBD8D1C5A7937D4C309B',
        }

        # 硬件参数
        self.hardware_params = {
            'stbinfo': '4C3263999F86300E13818AA92B45A5B166425501B112038B80E3DDC38EC7A1ECB3FC219932988AF1E5490D58DDFBBD443DB8575449D1A4ED0AF5AB8439ACE770AD5532BEC1D42163FDBC1515C5D09CDDC202D2EC39EF8D7CD633C7106D7ABF4FEE4EA3C154598BA9CEF102B947537D5A7B2E28DC26B14CDFB90BF5284DB233A6',
            'stbtype': 'B860AV3.2-T',
            'drmsupplier': '0',
            'prmid': '',
            'easip': '10.255.9.22',
            'networkid': '1',
            'stbmac': '18:5e:0b:93:f4:4c'
        }

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 9; B860AV3.2-T Build/F6100699007048800000) (ztebw,1.0.1,ZTE,blink,7105)AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36',
            'Accept-Language': 'zh-cn',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

        self.current_token = None
        self.jsessionid = None
        self.current_base_url = None

        print("=" * 70)
        print("贵州电信IPTV HTML获取工具 - 简化版")
        print("=" * 70)

    def detect_and_fix_encoding(self, response) -> str:
        """检测并修复响应编码，返回正确解码的文本"""
        # 保存原始内容
        content = response.content

        # 方法1: 尝试从HTTP头获取编码
        content_type = response.headers.get('content-type', '').lower()
        if 'charset=' in content_type:
            charset_match = re.search(r'charset=([^\s;]+)', content_type)
            if charset_match:
                encoding = charset_match.group(1).lower()
                if encoding == 'utf8':
                    encoding = 'utf-8'
                elif encoding == 'gb2312':
                    encoding = 'gbk'

                try:
                    return content.decode(encoding, errors='ignore')
                except:
                    print(f"    ⚠️ HTTP头编码{encoding}解码失败，尝试其他编码")

        # 方法2: 尝试从HTML meta标签获取编码
        try:
            # 先使用latin-1解码来查找meta标签
            temp_text = content.decode('latin-1', errors='ignore')
            charset_match = re.search(r'<meta[^>]*charset=["\']?([^"\'>]+)', temp_text, re.IGNORECASE)
            if charset_match:
                encoding = charset_match.group(1).lower()
                if encoding == 'utf8':
                    encoding = 'utf-8'
                elif encoding == 'gb2312':
                    encoding = 'gbk'

                if encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']:
                    try:
                        return content.decode(encoding, errors='ignore')
                    except:
                        print(f"    ⚠️ meta标签编码{encoding}解码失败")
        except:
            pass

        # 方法3: 尝试常见编码
        encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin-1']

        for encoding in encodings_to_try:
            try:
                # 尝试解码
                decoded = content.decode(encoding, errors='strict')
                # 检查是否有明显的中文字符
                chinese_chars = sum(1 for char in decoded[:2000] if '\u4e00' <= char <= '\u9fff')
                if chinese_chars > 20:  # 至少有20个中文字符
                    print(f"    检测到编码: {encoding} (包含{chinese_chars}个中文字符)")
                    return decoded
            except:
                continue

        # 方法4: 最后使用UTF-8并忽略错误
        print("    ⚠️ 无法确定编码，默认使用UTF-8")
        return content.decode('utf-8', errors='ignore')

    def save_response(self, filename: str, content: str, note: str = ""):
        """保存响应内容为UTF-8编码文件"""
        try:
            with open(filename, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)

            # 同时保存一份原始二进制响应，以便调试
            try:
                # 如果是响应对象，保存原始内容
                if hasattr(content, 'encode'):
                    with open(filename.replace('.html', '.raw.bin'), 'wb') as f:
                        f.write(content.encode('utf-8', errors='ignore'))
            except:
                pass

            msg = f"📁 {filename} ({len(content)} 字符)"
            if note:
                msg += f" - {note}"
            print(f"  {msg}")
            return True
        except Exception as e:
            print(f"  ⚠️ 保存失败 {filename}: {e}")
            return False

    def step1_complete_authentication(self) -> Tuple[bool, Optional[str]]:
        """步骤1: 完整认证流程"""
        print("\n[1] 执行完整认证流程...")

        try:
            # 1.1 初始认证
            print("  1.1 初始认证请求")
            auth_url = f"{self.config['base_url']}/gzitv-epg/ApiTerminal/BootAuth"
            params = {'UserID': self.config['user_id'], 'Action': 'Login'}

            resp = self.session.get(auth_url, params=params, timeout=15)
            resp_text = self.detect_and_fix_encoding(resp)
            self.save_response('step1_1_auth_init.html', resp_text, f"状态码: {resp.status_code}")

            # 1.2 提交Authenticator
            print("  1.2 提交Authenticator")
            auth_url = f"{self.config['base_url']}/gzitv-epg/ApiTerminal/AuthInfo"
            data = {
                'UserID': self.config['user_id'],
                'Authenticator': self.config['authenticator']
            }

            resp = self.session.post(auth_url, data=data, timeout=15)
            resp_text = self.detect_and_fix_encoding(resp)
            self.save_response('step1_2_auth_response.html', resp_text, f"状态码: {resp.status_code}")

            # 提取UserToken
            token_match = re.search(r"CTCSetConfig\s*\(\s*['\"]UserToken['\"][^,]*,\s*['\"]([^'\"]+)['\"]", resp_text)
            if token_match:
                self.current_token = token_match.group(1)
            elif 'UserToken' in self.session.cookies:
                self.current_token = self.session.cookies['UserToken']

            if not self.current_token:
                print("  ❌ 无法提取UserToken")
                return False, None

            print(f"  ✅ 获得UserToken: {self.current_token[:30]}...")

            # 提取EPG域名
            epg_domain_match = re.search(r"CTCSetConfig\s*\(\s*['\"]EPGDomain['\"][^,]*,\s*['\"]([^'\"]+)['\"]",
                                         resp_text)
            epg_domain = epg_domain_match.group(
                1) if epg_domain_match else 'http://10.255.9.60:8080/iptvepg/function/index.jsp'

            user_group_match = re.search(r"CTCSetConfig\s*\(\s*['\"]UserGroupNMB['\"][^,]*,\s*['\"]([^'\"]+)['\"]",
                                         resp_text)
            user_group = user_group_match.group(1) if user_group_match else '1091'

            epg_group_match = re.search(r"CTCSetConfig\s*\(\s*['\"]EPGGroupNMB['\"][^,]*,\s*['\"]([^'\"]+)['\"]",
                                        resp_text)
            epg_group = epg_group_match.group(1) if epg_group_match else '-1'

            # 构建初始EPG URL
            initial_epg_url = (
                f"{epg_domain}?UserGroupNMB={user_group}"
                f"&EPGGroupNMB={epg_group}"
                f"&UserToken={self.current_token}"
                f"&UserID={self.config['user_id']}"
                f"&STBID=null"
            )

            print(f"  ✅ 构建EPG地址成功: {initial_epg_url}")
            return True, initial_epg_url

        except Exception as e:
            print(f"  ❌ 认证异常: {e}")
            import traceback
            traceback.print_exc()
            return False, None

    def step2_navigate_to_hardware_page(self, start_url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """步骤2: 导航到硬件认证页面"""
        print("\n[2] 导航到硬件认证页面...")

        current_url = start_url
        redirect_count = 0
        max_redirects = 10

        while redirect_count < max_redirects:
            redirect_count += 1
            print(f"  重定向 {redirect_count}: {current_url}")

            try:
                resp = self.session.get(current_url, timeout=15, allow_redirects=False)
                resp_text = self.detect_and_fix_encoding(resp)
                self.save_response(f'step2_redirect_{redirect_count}.html', resp_text,
                                   f"状态码: {resp.status_code}")

                # 更新基础URL
                parsed = urlparse(current_url)
                self.current_base_url = f"{parsed.scheme}://{parsed.netloc}"

                # 检查JSESSIONID
                if 'JSESSIONID' in resp.cookies:
                    self.jsessionid = resp.cookies['JSESSIONID']
                    print(f"    ✅ JSESSIONID: {self.jsessionid}")

                # 检查是否是硬件认证页面
                if self.is_hardware_auth_page(resp_text):
                    print(f"    ✅ 到达硬件认证页面")
                    return True, current_url, resp_text

                # 检查重定向
                if resp.status_code in [301, 302, 303, 307, 308]:
                    if 'Location' in resp.headers:
                        location = resp.headers['Location']
                        print(f"    🔄 重定向到: {location}")
                        if not location.startswith('http'):
                            location = urljoin(self.current_base_url, location)
                        current_url = location
                        continue

                # 查找JavaScript重定向
                next_url = self.find_js_redirect(resp_text, current_url)
                if next_url:
                    print(f"    🔄 JavaScript重定向到: {next_url}")
                    current_url = next_url
                    continue

                print(f"    ⚠️ 没有找到重定向，停止导航")
                break

            except Exception as e:
                print(f"    ❌ 请求异常: {e}")
                break

        return False, None, None

    def is_hardware_auth_page(self, content: str) -> bool:
        """判断是否是硬件认证页面"""
        return ('funcportalauth.jsp' in content or
                'stbinfo' in content or
                'gotoEPG()' in content)

    def find_js_redirect(self, content: str, base_url: str) -> Optional[str]:
        """查找JavaScript重定向"""
        patterns = [
            r'document\.location\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'window\.location\.href\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'window\.location\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'top\.location\.href\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'top\.document\.location\s*=\s*[\'"]([^\'"]+)[\'"]'
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                url = match.group(1)
                if url.startswith('/'):
                    # 相对路径，使用当前基础URL
                    if self.current_base_url:
                        return f"{self.current_base_url}{url}"
                elif not url.startswith('http'):
                    # 相对路径，使用当前页面URL的基础
                    return urljoin(base_url, url)
                else:
                    return url

        return None

    def extract_form_data(self, content: str) -> Tuple[Optional[str], Optional[Dict]]:
        """提取表单数据和action"""
        # 查找form标签
        form_pattern = r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</form>'
        form_match = re.search(form_pattern, content, re.IGNORECASE)

        if not form_match:
            return None, None

        action = form_match.group(1)
        form_html = form_match.group(2)

        # 提取所有input字段
        input_pattern = r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\'][^>]*>'
        input_matches = re.findall(input_pattern, form_html, re.IGNORECASE)

        form_data = {}
        for name, value in input_matches:
            form_data[name] = html.unescape(value)

        return action, form_data

    def step3_submit_hardware_with_mac(self, page_url: str, page_content: str) -> Tuple[bool, Optional[str]]:
        """步骤3: 提交硬件信息"""
        print("\n[3] 提交硬件信息...")

        try:
            # 提取表单提交地址
            form_action, form_data = self.extract_form_data(page_content)

            if not form_action or not form_data:
                print("  ❌ 无法提取表单数据")
                return False, None

            # 补全form_action
            if not form_action.startswith('http'):
                form_action = urljoin(page_url, form_action)

            print(f"  表单地址: {form_action}")

            # 更新表单数据
            form_data.update({
                'stbinfo': self.hardware_params['stbinfo'],
                'prmid': self.hardware_params['prmid'],
                'easip': self.hardware_params['easip'],
                'networkid': self.hardware_params['networkid'],
                'stbtype': self.hardware_params['stbtype'],
                'drmsupplier': self.hardware_params['drmsupplier']
            })

            print(f"  提交硬件信息:")
            print(f"    stbtype: {self.hardware_params['stbtype']}")
            print(f"    drmsupplier: {self.hardware_params['drmsupplier']}")
            print(f"    stbmac: {self.hardware_params['stbmac']}")

            # 提交表单
            self.session.headers['Referer'] = page_url
            resp = self.session.post(form_action, data=form_data, timeout=20)
            resp_text = self.detect_and_fix_encoding(resp)

            self.save_response('step3_hardware_response.html', resp_text,
                               f"状态码: {resp.status_code}")

            # 分析响应
            return self.analyze_hardware_response(resp_text, form_action)

        except Exception as e:
            print(f"  ❌ 硬件信息提交异常: {e}")
            import traceback
            traceback.print_exc()
            return False, None

    def analyze_hardware_response(self, content: str, referer_url: str) -> Tuple[bool, Optional[str]]:
        """分析硬件认证响应"""
        print("  分析硬件认证响应...")

        # 查找JavaScript重定向
        redirect_url = self.find_js_redirect(content, referer_url)
        if redirect_url:
            print(f"  ✅ 发现重定向: {redirect_url}")
            return True, redirect_url

        # 检查是否直接包含setInfoForFatClient或skipFrame等函数
        if 'skipFrame' in content or 'setInfoForFatClient' in content:
            print(f"  ✅ 需要继续重定向流程")
            # 从响应中提取新的重定向
            if 'frame.jsp' in content:
                base_url = referer_url.rsplit('/', 1)[0]
                return True, f"{base_url}/frame.jsp"

        print(f"  ⚠️ 需要进一步分析响应")
        return True, None

    def step4_handle_redirect_chain(self) -> bool:
        """步骤4: 处理重定向链并获取最终HTML"""
        print("\n[4] 处理重定向链并获取最终HTML...")

        try:
            # 1. 访问frame.jsp
            print("  1. 访问frame.jsp")
            frame_url = f"{self.current_base_url}/iptvepg/function/frame.jsp"
            resp = self.session.get(frame_url, timeout=15)
            resp_text = self.detect_and_fix_encoding(resp)
            self.save_response('step4_frame.jsp.html', resp_text,
                               f"状态码: {resp.status_code}")

            # 2. 提取并提交表单到frameset_judger.jsp
            print("  2. 提交到frameset_judger.jsp")
            form_action, form_data = self.extract_form_data(resp_text)
            if form_action and form_data:
                if not form_action.startswith('http'):
                    form_action = urljoin(frame_url, form_action)

                print(f"    frameset_judger.jsp地址: {form_action}")
                resp = self.session.post(form_action, data=form_data, timeout=15)
                resp_text = self.detect_and_fix_encoding(resp)
                self.save_response('step4_frameset_judger.jsp.html', resp_text,
                                   f"状态码: {resp.status_code}")
            else:
                print("  ⚠️ 无法提取frameset_judger.jsp表单，尝试直接访问")
                frameset_judger_url = f"{self.current_base_url}/iptvepg/function/frameset_judger.jsp?picturetype=1,3,5"
                resp = self.session.get(frameset_judger_url, timeout=15)
                resp_text = self.detect_and_fix_encoding(resp)
                self.save_response('step4_frameset_judger.jsp.html', resp_text,
                                   f"状态码: {resp.status_code}")

            # 3. 提取并提交表单到frameset_builder.jsp
            print("  3. 提交到frameset_builder.jsp")
            form_action, form_data = self.extract_form_data(resp_text)
            if form_action and form_data:
                if not form_action.startswith('http'):
                    form_action = urljoin(self.current_base_url + "/iptvepg/function/", form_action)

                # 添加必要的参数
                form_data.update({
                    'MAIN_WIN_SRC': '/iptvepg/frame1081/portal.jsp',
                    'NEED_UPDATE_STB': '1',
                    'BUILD_ACTION': 'FRAMESET_BUILDER',
                    'hdmistatus': ''
                })

                print(f"    frameset_builder.jsp地址: {form_action}")
                resp = self.session.post(form_action, data=form_data, timeout=15)
                resp_text = self.detect_and_fix_encoding(resp)

                # 保存最终HTML
                self.save_response('final_frameset_builder.html', resp_text,
                                   f"状态码: {resp.status_code}")

                # 同时尝试使用GBK编码保存一份，以便对比
                try:
                    with open('final_frameset_builder_gbk.html', 'w', encoding='gbk', errors='ignore') as f:
                        f.write(resp.content.decode('gbk', errors='ignore'))
                    print("    ✅ 已保存GBK编码版本用于对比: final_frameset_builder_gbk.html")
                except:
                    pass

                print("  ✅ 已保存最终HTML: final_frameset_builder.html")
                return True
            else:
                print("  ⚠️ 无法提取frameset_builder.jsp表单，尝试直接访问")
                # 尝试直接构造URL
                frameset_builder_url = f"{self.current_base_url}/iptvepg/function/frameset_builder.jsp"
                post_data = {
                    'MAIN_WIN_SRC': '/iptvepg/frame1081/portal.jsp',
                    'NEED_UPDATE_STB': '1',
                    'BUILD_ACTION': 'FRAMESET_BUILDER',
                    'hdmistatus': ''
                }
                resp = self.session.post(frameset_builder_url, data=post_data, timeout=15)
                resp_text = self.detect_and_fix_encoding(resp)

                # 保存最终HTML
                self.save_response('final_frameset_builder.html', resp_text,
                                   f"状态码: {resp.status_code}")

                # 同时尝试使用GBK编码保存一份，以便对比
                try:
                    with open('final_frameset_builder_gbk.html', 'w', encoding='gbk', errors='ignore') as f:
                        f.write(resp.content.decode('gbk', errors='ignore'))
                    print("    ✅ 已保存GBK编码版本用于对比: final_frameset_builder_gbk.html")
                except:
                    pass

                print("  ✅ 已保存最终HTML: final_frameset_builder.html")
                return True

        except Exception as e:
            print(f"  ❌ 重定向链处理异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run(self):
        """运行完整流程"""
        print("\n🚀 开始执行完整流程...")

        try:
            # 步骤1: 认证
            print("\n" + "=" * 70)
            print("步骤1: 认证")
            print("=" * 70)

            auth_ok, epg_url = self.step1_complete_authentication()
            if not auth_ok:
                print("\n❌ 认证失败")
                return False

            # 步骤2: 导航
            print("\n" + "=" * 70)
            print("步骤2: 导航")
            print("=" * 70)

            nav_ok, hw_page_url, hw_page_content = self.step2_navigate_to_hardware_page(epg_url)
            if not nav_ok:
                print("\n❌ 导航失败")
                return False

            # 步骤3: 硬件认证
            print("\n" + "=" * 70)
            print("步骤3: 硬件认证")
            print("=" * 70)

            hw_ok, next_url = self.step3_submit_hardware_with_mac(hw_page_url, hw_page_content)
            if not hw_ok:
                print("\n❌ 硬件认证失败")
                return False

            # 步骤4: 处理重定向链并获取最终HTML
            print("\n" + "=" * 70)
            print("步骤4: 处理重定向链并获取最终HTML")
            print("=" * 70)

            redirect_ok = self.step4_handle_redirect_chain()
            if not redirect_ok:
                print("\n❌ 重定向链处理失败")
                return False

            print("\n" + "=" * 70)
            print("🎉 恭喜！最终HTML获取成功！")
            print("=" * 70)
            print("\n📁 生成的文件:")
            print("  1. final_frameset_builder.html - 包含频道数据的最终HTML(UTF-8)")
            print("  2. final_frameset_builder_gbk.html - GBK编码版本用于对比")
            print("  3. 其他步骤的HTML文件用于调试")
            print("\n⚠️ 注意:")
            print("  如果final_frameset_builder.html仍有乱码，请尝试使用")
            print("  final_frameset_builder_gbk.html 进行提取")
            print("\n🔧 下一步:")
            print("  请使用单独的脚本从 final_frameset_builder.html 或")
            print("  final_frameset_builder_gbk.html 中提取频道数据")
            return True

        except Exception as e:
            print(f"\n❌ 流程异常: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    print("\n⚠️ 重要提醒:")
    print("  1. 确保连接在IPTV专网（能访问10.255.x.x地址）")
    print("  2. 脚本使用真实MAC地址: 18:5e:0b:93:f4:4c")
    print("  3. 如果authenticator过期，请从最新抓包更新")
    print("  4. 此脚本只获取HTML，不提取频道数据")
    print("  5. 会自动检测编码并生成UTF-8和GBK两个版本")

    print(f"\n📋 使用的参数:")
    print(f"  用户ID: {GZITVHTMLFetcher().config['user_id']}")
    print(f"  MAC地址: {GZITVHTMLFetcher().hardware_params['stbmac']}")
    print(f"  机顶盒型号: {GZITVHTMLFetcher().hardware_params['stbtype']}")

    input("\n按Enter键开始执行...")

    fetcher = GZITVHTMLFetcher()
    success = fetcher.run()

    if success:
        print(f"\n✨ 任务完成！")
        print(f"   请在当前目录查看生成的 final_frameset_builder.html 文件")
        print(f"   如果仍有乱码，请尝试 final_frameset_builder_gbk.html")
    else:
        print(f"\n❌ 任务失败，请检查错误信息")
        print(f"   请查看保存的HTML文件以调试")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()