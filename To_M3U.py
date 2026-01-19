#!/usr/bin/env python3
"""
贵州电信IPTV M3U生成器
从HTML中提取频道信息并生成规范的M3U文件
"""

import re
import json
import html
import sys
import os
from typing import List, Dict, Tuple
from collections import defaultdict


class GZIPTVM3UGenerator:
    def __init__(self, html_file: str = 'final_frameset_builder.html'):
        self.html_file = html_file
        self.channels = []

        print("=" * 70)
        print("贵州电信IPTV M3U生成器")
        print("=" * 70)

    def load_html(self) -> str:
        """加载HTML文件"""
        print(f"📖 加载文件: {self.html_file}")

        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']

        for encoding in encodings:
            try:
                with open(self.html_file, 'r', encoding=encoding) as f:
                    content = f.read()
                    print(f"  使用 {encoding} 编码成功，长度: {len(content)} 字符")

                    # 检查是否包含关键信息
                    if 'ChannelName=' in content and 'ChannelSDP=' in content:
                        print(f"  ✅ 找到频道数据")
                        return content
                    else:
                        print(f"  ⚠️  未找到频道数据，尝试其他编码")
                        continue
            except UnicodeDecodeError:
                print(f"  ❌ {encoding} 编码失败")
                continue
            except FileNotFoundError:
                print(f"  ❌ 文件不存在: {self.html_file}")
                sys.exit(1)

        print("❌ 所有编码尝试失败")
        sys.exit(1)

    def extract_channels(self, content: str) -> List[Dict]:
        """从HTML中提取频道信息"""
        print("\n🔍 提取频道信息...")

        channels = []

        # 查找所有包含 ChannelName 和 ChannelSDP 的片段
        # 格式: ChannelName="..."ChannelSDP="..."
        pattern = r'ChannelName="([^"]+)"[^>]*?ChannelSDP="([^"]+)"'
        matches = re.findall(pattern, content)

        print(f"  找到 {len(matches)} 个频道配置")

        for i, (channel_name, channel_sdp) in enumerate(matches):
            try:
                # HTML解码频道名称
                channel_name = html.unescape(channel_name)

                # 从SDP中提取igmp和rtsp链接
                igmp_url = ""
                rtsp_url = ""

                # 格式: igmp://...|rtsp://...
                if '|' in channel_sdp:
                    parts = channel_sdp.split('|')
                    for part in parts:
                        part = part.strip()
                        if part.startswith('igmp://'):
                            igmp_url = part
                        elif part.startswith('rtsp://'):
                            # 移除可能的参数（如?AuthInfo）
                            if '?' in part:
                                rtsp_url = part.split('?')[0]
                            else:
                                rtsp_url = part
                else:
                    # 如果没有分隔符，整个SDP可能是igmp链接
                    if channel_sdp.startswith('igmp://'):
                        igmp_url = channel_sdp

                if not igmp_url:
                    print(f"  ⚠️  第 {i + 1} 个频道没有igmp链接，跳过")
                    continue

                # 清理频道名称：移除"new"和多余的括号内容
                clean_name = self.clean_channel_name(channel_name)

                # 分类
                category = self.categorize_channel(clean_name)

                # 添加排序键
                sort_key = self.get_sort_key(clean_name, category)

                # 添加到列表
                channels.append({
                    'original_name': channel_name,
                    'name': clean_name,
                    'igmp_url': igmp_url,
                    'rtsp_url': rtsp_url,
                    'category': category,
                    'sort_key': sort_key
                })

                print(f"  ✓ {clean_name} [{category}]")

            except Exception as e:
                print(f"  ⚠️  解析第 {i + 1} 个频道失败: {e}")
                continue

        return channels

    def clean_channel_name(self, name: str) -> str:
        """清理频道名称"""
        # 移除"new"字样
        name = name.replace('new', '').replace('NEW', '')

        # 移除括号内容
        name = re.sub(r'\([^)]*\)', '', name)  # 英文括号
        name = re.sub(r'\（[^）]*\）', '', name)  # 中文括号

        # 清理空格
        name = ' '.join(name.split())

        return name.strip()

    def categorize_channel(self, name: str) -> str:
        """频道分类"""
        # 央视分类
        cctv_keywords = ['CCTV', '中央', '央视', 'CGTN']
        for keyword in cctv_keywords:
            if keyword in name:
                return '央视'

        # 卫视分类
        if '卫视' in name:
            return '卫视'

        # 贵州分类
        guizhou_keywords = ['贵州', '贵阳', '黔', '毕节', '安顺', '铜仁', '遵义', '雷山', '仁怀','六盘水', '凯里','六枝', '观山湖', '瓮安', '思南', '桐梓', '云岩']
        for keyword in guizhou_keywords:
            if keyword in name:
                return '贵州'

        # 其他分类
        return '其他'

    def get_sort_key(self, name: str, category: str) -> tuple:
        """获取排序键"""
        if category == '央视':
            # 央视频道按照CCTV1, CCTV2, ... 这样的数字顺序排序
            # 提取数字部分
            import re
            # 查找数字
            numbers = re.findall(r'\d+', name)
            if numbers:
                # 使用第一个找到的数字
                try:
                    num = int(numbers[0])
                    # 返回一个元组，确保数字小的在前
                    return (0, num, name)
                except:
                    pass

            # 如果没有数字，返回一个大数字确保排在后面
            return (0, 9999, name)
        else:
            # 其他分类按照首字母排序
            if not name:
                return ('Z', name)

            first_char = name[0]

            # 如果是中文字符，获取拼音首字母
            if '\u4e00' <= first_char <= '\u9fff':
                # 常见频道首字母映射
                pinyin_map = {
                    'C': ['C', 'c', '中', '重', '川'],
                    'A': ['A', 'a', '安', '澳'],
                    'B': ['B', 'b', '北', '百', '八'],
                    'D': ['D', 'd', '大', '东', '都'],
                    'E': ['E', 'e', '二', '鄂'],
                    'F': ['F', 'f', '福', '方'],
                    'G': ['G', 'g', '贵', '广', '甘'],
                    'H': ['H', 'h', '湖', '河', '海', '黑'],
                    'J': ['J', 'j', '江', '吉', '九'],
                    'K': ['K', 'k', '康', '卡'],
                    'L': ['L', 'l', '六', '辽', '龙'],
                    'M': ['M', 'm', '民', '美'],
                    'N': ['N', 'n', '宁', '南', '农'],
                    'Q': ['Q', 'q', '青', '七', '黔'],
                    'R': ['R', 'r', '人', '日'],
                    'S': ['S', 's', '三', '上', '四', '山', '四', '陕'],
                    'T': ['T', 't', '天', '台'],
                    'W': ['W', 'w', '五', '卫', '晚'],
                    'X': ['X', 'x', '西', '新', '湘', '厦'],
                    'Y': ['Y', 'y', '一', '央', '云', '延', '宜'],
                    'Z': ['Z', 'z', '藏', '浙', '重', '中']
                }

                for key, chars in pinyin_map.items():
                    if first_char in chars:
                        return (key, name)

                return (first_char.upper(), name)
            else:
                # 英文字母直接返回
                return (first_char.upper(), name)

    def sort_channels(self, channels: List[Dict]) -> Dict[str, List[Dict]]:
        """按分类和排序键排序"""
        # 按分类分组
        grouped = defaultdict(list)
        for channel in channels:
            grouped[channel['category']].append(channel)

        # 对每个分类内的频道按排序键排序
        for category in grouped:
            if category == '央视':
                # 央视按照数字排序
                grouped[category] = sorted(grouped[category], key=lambda x: x['sort_key'])
            else:
                # 其他分类按照首字母排序
                grouped[category] = sorted(grouped[category], key=lambda x: x['sort_key'])

        return grouped

    def parse_html(self) -> bool:
        """解析HTML文件"""
        content = self.load_html()
        if not content:
            return False

        self.channels = self.extract_channels(content)

        if not self.channels:
            print("❌ 未提取到任何频道")
            return False

        print(f"\n✅ 成功提取 {len(self.channels)} 个频道")
        return True

    def generate_m3u(self, udpxy_url: str = "http://192.168.1.44:5140/rtp") -> str:
        """生成M3U内容"""
        print(f"\n🎬 生成M3U文件 (UDPXY: {udpxy_url})...")

        # 按分类和排序键排序
        grouped_channels = self.sort_channels(self.channels)

        # 分类顺序
        categories_order = ['央视', '卫视', '贵州', '其他']

        m3u_lines = ['#EXTM3U']

        for category in categories_order:
            if category not in grouped_channels or not grouped_channels[category]:
                continue

            channels = grouped_channels[category]

            # 添加分类注释
            m3u_lines.append(f'\n# 分类: {category}')

            for channel in channels:
                # 提取组播IP和端口
                igmp_match = re.search(r'igmp://([^:]+):(\d+)', channel['igmp_url'])
                if not igmp_match:
                    continue

                ip = igmp_match.group(1)
                port = igmp_match.group(2)

                # 构建播放地址
                play_url = f"{udpxy_url}/{ip}:{port}?fcc=10.255.5.32:8027"

                # 构建EXTINF行
                extinf_parts = [
                    f'#EXTINF:-1',
                    f'tvg-name="{channel["name"]}"',
                    f'category="贵州电信iptv"',
                    f'group-title="{category}"'
                ]

                # 如果有rtsp链接，添加时移信息
                if channel['rtsp_url']:
                    # 移除URL末尾的斜杠（如果有）
                    rtsp_url = channel['rtsp_url'].rstrip('/')
                    catchup_source = f"{rtsp_url}/?playseek=${{(b)yyyyMMddHHmmss}}-${{(e)yyyyMMddHHmmss}}"
                    extinf_parts.append(f'catchup="default"')
                    extinf_parts.append(f'catchup-source="{catchup_source}"')

                extinf_line = ' '.join(extinf_parts) + f',{channel["name"]}'

                m3u_lines.append(extinf_line)
                m3u_lines.append(play_url)

        return '\n'.join(m3u_lines)

    def save_m3u(self, m3u_content: str, filename: str = "iptv_channels.m3u") -> bool:
        """保存M3U文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(m3u_content)

            print(f"💾 M3U文件已保存: {filename}")
            return True
        except Exception as e:
            print(f"❌ 保存M3U文件失败: {e}")
            return False

    def save_details(self, filename: str = "channels_detail.txt") -> bool:
        """保存频道详细信息"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("贵州电信IPTV频道列表\n")
                f.write("=" * 70 + "\n\n")

                # 按分类和排序键排序
                grouped_channels = self.sort_channels(self.channels)

                # 分类顺序
                categories_order = ['央视', '卫视', '贵州', '其他']

                for category in categories_order:
                    if category not in grouped_channels or not grouped_channels[category]:
                        continue

                    channels = grouped_channels[category]

                    f.write(f"\n【{category}】({len(channels)}个)\n")
                    f.write("-" * 70 + "\n")

                    for i, channel in enumerate(channels):
                        f.write(f"{i + 1:3d}. {channel['name']}\n")
                        f.write(f"     原名称: {channel['original_name']}\n")
                        f.write(f"     组播地址: {channel['igmp_url']}\n")
                        if channel['rtsp_url']:
                            f.write(f"     时移地址: {channel['rtsp_url']}\n")
                        f.write("\n")

            print(f"📋 详细信息已保存: {filename}")
            return True
        except Exception as e:
            print(f"❌ 保存详细信息失败: {e}")
            return False

    def run(self, udpxy_url: str = "http://192.168.1.44:5140/rtp") -> bool:
        """运行生成流程"""
        print("\n" + "=" * 70)
        print("开始生成M3U文件")
        print("=" * 70)

        # 解析HTML
        if not self.parse_html():
            return False

        # 生成M3U
        m3u_content = self.generate_m3u(udpxy_url)

        # 保存文件
        if not self.save_m3u(m3u_content):
            return False

        # 保存详细信息
        self.save_details()

        print("\n" + "=" * 70)
        print("🎉 M3U文件生成完成！")
        print("=" * 70)
        print("\n📁 生成的文件:")
        print("  1. iptv_channels.m3u - M3U播放列表")
        print("  2. channels_detail.txt - 频道详细信息")
        print("\n📊 频道统计:")

        # 显示分类统计
        grouped_channels = self.sort_channels(self.channels)
        categories_order = ['央视', '卫视', '贵州', '其他']

        for category in categories_order:
            if category in grouped_channels:
                count = len(grouped_channels[category])
                print(f"  {category}: {count}个")

        print(f"\n📱 使用方法:")
        print("  1. 确保UDPXY服务器运行在: 192.168.1.44:5140")
        print("  2. 用VLC/PotPlayer打开 iptv_channels.m3u")
        print("  3. 如需修改UDPXY地址，运行: python script.py [udpxy_url]")

        return True


def main():
    import sys

    print("\n⚠️ 重要提醒:")
    print("  1. 确保已运行HTML获取脚本并生成 final_frameset_builder.html")
    print("  2. 确保UDPXY服务器已正确配置")
    print("  3. 默认UDPXY地址: http://192.168.1.44:5140/rtp")

    # 检查文件是否存在
    if not os.path.exists('final_frameset_builder.html'):
        print("\n❌ 未找到 final_frameset_builder.html")
        print("请先运行HTML获取脚本")
        sys.exit(1)

    # 获取UDPXY地址（可选参数）
    udpxy_url = "http://192.168.1.44:5140/rtp"
    if len(sys.argv) > 1:
        udpxy_url = sys.argv[1]
        print(f"使用指定的UDPXY地址: {udpxy_url}")
    else:
        print(f"使用默认UDPXY地址: {udpxy_url}")

    input("\n按Enter键开始生成M3U...")

    generator = GZIPTVM3UGenerator()
    success = generator.run(udpxy_url)

    if success:
        print(f"\n✨ M3U生成完成！")
    else:
        print(f"\n❌ M3U生成失败")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()