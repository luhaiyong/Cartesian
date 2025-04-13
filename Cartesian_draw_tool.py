import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import TextBox, Button, RadioButtons
from tkinter import Tk, filedialog
import os
from collections import defaultdict
from matplotlib import rcParams
import weakref
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
# 设置支持中文的字体
rcParams['font.sans-serif'] = ['STFangsong', 'Arial']  # 添加英文字体
rcParams['axes.unicode_minus'] = False

# 初始化Tkinter
root = Tk()
root.withdraw()


# ========== 多语言支持 ==========
class Language:
    def __init__(self):
        self.current_lang = 'en'  # 默认中文

    def set_language(self, lang):
        self.current_lang = lang

    def t(self, zh, en):
        return zh if self.current_lang == 'zh' else en


lang = Language()

# 文本资源
TEXTS = {
    'title': ('笛卡尔坐标系（支持旋转）', 'Cartesian Coordinate System (Rotatable)'),
    'x_axis': ('X轴', 'X Axis'),
    'y_axis': ('Y轴', 'Y Axis'),
    'rotated_x': ('Y轴（向左为正）', 'Y Axis (Left Positive)'),
    'rotated_y': ('X轴（向上为正）', 'X Axis (Up Positive)'),
    'panel_title': ('控制面板', 'Control Panel'),
    'load_file': ('加载文件', 'Load File'),
    'add_point': ('添加点 (x,y)', 'Add Point (x,y)'),
    'file_no': ('文件序号', 'File No.'),
    'clear_selected': ('清除选中文件', 'Clear Selected'),
    'display_mode': ('显示模式', 'Display Mode'),
    'points_only': ('仅点', 'Points Only'),
    'line': ('连线', 'Line'),
    'closed': ('闭合曲线', 'Closed Curve'),
    'rotate': ('旋转坐标系', 'Rotate Coordinates'),
    'clear_all': ('清除所有', 'Clear All'),
    'file_list': ('已加载文件', 'Loaded Files'),
    'no_files': ('无已加载文件', 'No Files Loaded'),
    'custom_points': ('自定义点', 'Custom Points'),
    'point_mode': ('点', 'Points'),
    'line_mode': ('线', 'Line'),
    'closed_mode': ('闭合', 'Closed'),
    'input_file_no': ('请输入文件序号', 'Please input file number'),
    'input_coord': ('请输入有效坐标，如: 3.5,-2.1', 'Please input valid coordinates, e.g. 3.5,-2.1'),
    'panel_expand': ('控制面板 ▲', 'Control Panel ▲'),
    'panel_collapse': ('控制面板 ▼', 'Control Panel ▼')
}

# 全局变量
file_data = defaultdict(dict)
custom_points = {'x': [], 'y': []}
color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
current_colors = set()
hover_enabled = False
annot = None
rotated = False
panel_visible = False
panel_widgets = []
file_list_box = None
is_loading = False

# 创建图形
fig = plt.figure(figsize=(12, 8))
ax = plt.axes([0.1, 0.1, 0.7, 0.8])
plt.subplots_adjust(right=0.8)


# ========== 核心函数 ==========
def draw_axes():
    ax.clear()
    if rotated:
        ax.axhline(0, color='black', linewidth=0.5)
        ax.axvline(0, color='black', linewidth=0.5)
        ax.set_xlabel(lang.t(*TEXTS['rotated_x']), loc='right')
        ax.set_ylabel(lang.t(*TEXTS['rotated_y']), loc='top')
    else:
        ax.axhline(0, color='black', linewidth=0.5)
        ax.axvline(0, color='black', linewidth=0.5)
        ax.set_xlabel(lang.t(*TEXTS['x_axis']), loc='right')
        ax.set_ylabel(lang.t(*TEXTS['y_axis']), loc='top')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_title(lang.t(*TEXTS['title']), pad=20)


draw_axes()


def get_unused_color():
    for color in color_cycle:
        if color not in current_colors:
            current_colors.add(color)
            return color
    return np.random.rand(3, )


def hover(event):
    if annot is None or event.inaxes != ax:
        annot.set_visible(False)
        fig.canvas.draw_idle()
        return

    vis = False
    for sc in ax.collections:
        if not hasattr(sc, 'contains'):
            continue

        cont, ind = sc.contains(event)
        if cont:
            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos
            is_custom = (sc == ax.collections[-1] and len(custom_points['x']) > 0)

            if is_custom:
                idx = ind["ind"][0]
                text = f"({custom_points['x'][idx]:.2f}, {custom_points['y'][idx]:.2f})"
            else:
                for data in file_data.values():
                    if rotated:
                        x_data = [-y for y in data['y']]
                        y_data = data['x']
                    else:
                        x_data = data['x']
                        y_data = data['y']

                    matches = np.where(
                        (np.isclose(x_data, pos[0])) &
                        (np.isclose(y_data, pos[1]))
                    )[0]

                    if len(matches) > 0:
                        idx = matches[0]
                        text = f"({data['x'][idx]:.2f}, {data['y'][idx]:.2f})"
                        break

            annot.set_text(text)
            vis = True
            break

    annot.set_visible(vis)
    fig.canvas.draw_idle()


def update_plot():
    global hover_enabled, annot
    ax.clear()
    for text in ax.texts:
        text.remove()
    draw_axes()

    if hover_enabled:
        fig.canvas.mpl_disconnect(fig.canvas.manager.key_press_handler_id)
    fig.canvas.mpl_connect('motion_notify_event', hover)
    hover_enabled = True

    # 绘制文件数据
    for filepath, data in file_data.items():
        if len(data['x']) > 0:
            x_coords = np.array([-y for y in data['y']]) if rotated else np.array(data['x'])
            y_coords = np.array(data['x']) if rotated else np.array(data['y'])

            filename = os.path.basename(filepath)
            mode_display = {
                'points': lang.t(*TEXTS['point_mode']),
                'line': lang.t(*TEXTS['line_mode']),
                'closed': lang.t(*TEXTS['closed_mode'])
            }
            label = f"{filename} ({mode_display[data['mode']]})"

            sc = ax.scatter(x_coords, y_coords, c=data['color'], s=50,
                            edgecolors='black', label=label, picker=True)

            if data['mode'] in ('line', 'closed') and len(data['x']) > 1:
                if data['mode'] == 'closed':
                    x_coords = np.append(x_coords, x_coords[0])
                    y_coords = np.append(y_coords, y_coords[0])
                ax.plot(x_coords, y_coords, '-', alpha=0.5, color=data['color'])

    # 绘制自定义点
    if custom_points['x']:
        display_x = np.array([-y for y in custom_points['y']]) if rotated else np.array(custom_points['x'])
        display_y = np.array(custom_points['x']) if rotated else np.array(custom_points['y'])

        sc_custom = ax.scatter(display_x, display_y, c='green', s=80,
                               marker='*', edgecolors='black',
                               label=lang.t(*TEXTS['custom_points']), picker=True)

        for i, (x_disp, y_disp) in enumerate(zip(display_x, display_y)):
            ax.text(x_disp, y_disp, f'({custom_points["x"][i]:.1f}, {custom_points["y"][i]:.1f})',
                    fontsize=9, ha='left', va='bottom', color='green')

    # 注释框
    if annot is not None:
        annot.remove()
    annot = ax.annotate("", xy=(0, 0), xytext=(20, 20),
                        textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w", alpha=0.4),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)

    # 自动调整坐标范围
    all_x = []
    all_y = []
    for data in file_data.values():
        all_x.extend([-y for y in data['y']] if rotated else data['x'])
        all_y.extend(data['x'] if rotated else data['y'])
    if custom_points['x']:
        all_x.extend([-y for y in custom_points['y']] if rotated else custom_points['x'])
        all_y.extend(custom_points['x'] if rotated else custom_points['y'])

    if all_x and all_y:
        x_padding = (max(all_x) - min(all_x)) * 0.2
        y_padding = (max(all_y) - min(all_y)) * 0.2
        ax.set_xlim(min(all_x) - x_padding, max(all_x) + x_padding)
        ax.set_ylim(min(all_y) - y_padding, max(all_y) + y_padding)

    if rotated:
        xticks = ax.get_xticks()
        ax.set_xticklabels([f"{-x:g}" if x != 0 else '0' for x in xticks])

    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.draw()


def safe_file_dialog():
    global is_loading
    if is_loading:
        return None

    is_loading = True
    try:
        root.wm_attributes("-disabled", False)
        filepaths = filedialog.askopenfilenames(
            title=lang.t('选择坐标文件', 'Select Coordinate File'),
            filetypes=[(lang.t('文本文件', 'Text Files'), "*.txt"),
                       (lang.t('所有文件', 'All Files'), "*.*")])
        return filepaths
    finally:
        is_loading = False
        root.wm_attributes("-disabled", True)


def load_from_file(event=None):
    filepaths = safe_file_dialog()
    if not filepaths:
        return

    for filepath in filepaths:
        try:
            with open(filepath, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
                coords = [list(map(float, line.split(','))) for line in lines if line]

            if coords:
                x, y = zip(*coords)
                color = get_unused_color()
                file_data[filepath] = {
                    'x': list(x),
                    'y': list(y),
                    'color': color,
                    'mode': 'points'
                }
                print(lang.t(f"已加载 {len(x)} 个点来自 {os.path.basename(filepath)}",
                             f"Loaded {len(x)} points from {os.path.basename(filepath)}"))
        except Exception as e:
            print(lang.t(f"加载文件出错: {str(e)}", f"Error loading file: {str(e)}"))

    update_plot()
    update_file_list()


def clear_selected_file(event=None):
    if not file_data:
        return

    try:
        selected = int(selected_file_box.text.strip()) - 1
        if 0 <= selected < len(file_data):
            removed_file = list(file_data.keys())[selected]
            current_colors.discard(file_data[removed_file]['color'])
            del file_data[removed_file]
            update_plot()
            update_file_list()
    except:
        print(lang.t(*TEXTS['input_file_no']))


def add_point(text):
    try:
        x, y = map(float, text.strip('()').split(','))
        custom_points['x'].append(x)
        custom_points['y'].append(y)
        update_plot()
    except:
        print(lang.t(*TEXTS['input_coord']))


def clear_all_points(event=None):
    file_data.clear()
    current_colors.clear()
    custom_points['x'].clear()
    custom_points['y'].clear()
    draw_axes()
    update_file_list()


def change_mode(label):
    if not file_data:
        return

    try:
        selected = int(selected_file_box.text.strip()) - 1
        if 0 <= selected < len(file_data):
            filepath = list(file_data.keys())[selected]
            mode_mapping = {
                lang.t(*TEXTS['points_only']): 'points',
                lang.t(*TEXTS['line']): 'line',
                lang.t(*TEXTS['closed']): 'closed'
            }
            file_data[filepath]['mode'] = mode_mapping[label]
            update_plot()
            update_file_list()
    except:
        print(lang.t(*TEXTS['input_file_no']))


def rotate_coordinates(event=None):
    global rotated
    rotated = not rotated
    update_plot()


def update_file_list():
    if file_list_box is not None:
        file_list = []
        for i, (filepath, data) in enumerate(file_data.items(), 1):
            name = os.path.basename(filepath)
            mode = {'points': lang.t(*TEXTS['point_mode']),
                    'line': lang.t(*TEXTS['line_mode']),
                    'closed': lang.t(*TEXTS['closed_mode'])}[data['mode']]
            file_list.append(f"{i}. {name} ({mode})")
        file_list_box.set_val("\n".join(file_list) if file_list else lang.t(*TEXTS['no_files']))


def clear_panel12():
    global panel_widgets
    for widget in panel_widgets:
        try:
            widget.ax.remove()
        except:
            pass
    panel_widgets.clear()


def clear_panel():
    global panel_widgets
    for widget in panel_widgets:
        try:
            # 处理文本框特殊情况
            if isinstance(widget, TextBox):
                # 安全停止输入状态
                if hasattr(widget, '_ax_ref'):
                    ax = widget._ax_ref()
                    if ax is not None and ax.figure is not None:
                        widget.stop_typing()
                # 断开所有事件
                widget.disconnect_events()

            # 移除图形元素
            if hasattr(widget, 'ax') and widget.ax is not None:
                widget.ax.remove()
        except Exception as e:
            print(f"清理控件时忽略错误: {str(e)}")

    panel_widgets = []
    plt.pause(0.01)  # 允许GUI更新


def create_text_box(ax, label):
    text_box = TextBox(ax, label)
    # 添加弱引用处理
    text_box._ax_ref = weakref.ref(ax)
    return text_box


def show_control_panel():
    global panel_widgets, file_list_box
    clear_panel()

    # 布局参数
    left, width = 0.82, 0.15
    row_height = 0.05
    spacing = 0.02
    current_y = 0.9


    # 文件列表 (顶部)
    ax_list = plt.axes([left, current_y - 0.2, width, 0.18])
    file_list_box = create_text_box(ax_list, lang.t(*TEXTS['file_list']))
    panel_widgets.append(file_list_box)
    current_y -= 0.2 + spacing

    # 加载文件按钮
    ax_load = plt.axes([left, current_y - row_height, width, row_height])
    btn_load = Button(ax_load, lang.t(*TEXTS['load_file']),
                      color='lightgoldenrodyellow', hovercolor='gold')
    btn_load.on_clicked(load_from_file)
    panel_widgets.append(btn_load)
    current_y -= row_height + spacing

    # 添加点输入框
    ax_add = plt.axes([left, current_y - row_height, width, row_height])
    text_box = create_text_box(ax_add, lang.t(*TEXTS['add_point']))
    text_box.on_submit(add_point)
    panel_widgets.append(text_box)
    current_y -= row_height + spacing

    # 文件序号输入
    ax_select = plt.axes([left, current_y - row_height, width, row_height])
    global selected_file_box
    selected_file_box = create_text_box(ax_select, lang.t(*TEXTS['file_no']))
    panel_widgets.append(selected_file_box)
    current_y -= row_height + spacing

    # 清除选中文件
    ax_clear = plt.axes([left, current_y - row_height, width, row_height])
    btn_clear = Button(ax_clear, lang.t(*TEXTS['clear_selected']),
                       color='lightcoral', hovercolor='red')
    btn_clear.on_clicked(clear_selected_file)
    panel_widgets.append(btn_clear)
    current_y -= row_height + spacing * 2

    # 显示模式
    ax_mode = plt.axes([left, current_y - 0.12, width, 0.12])
    mode_radio = RadioButtons(ax_mode, [
        lang.t(*TEXTS['points_only']),
        lang.t(*TEXTS['line']),
        lang.t(*TEXTS['closed'])
    ], active=0)
    mode_radio.on_clicked(change_mode)
    panel_widgets.append(mode_radio)
    current_y -= 0.12 + spacing

    # 旋转坐标系
    ax_rotate = plt.axes([left, current_y - row_height, width, row_height])
    btn_rotate = Button(ax_rotate, lang.t(*TEXTS['rotate']),
                        color='lightblue', hovercolor='blue')
    btn_rotate.on_clicked(rotate_coordinates)
    panel_widgets.append(btn_rotate)
    current_y -= row_height + spacing

    # 清除所有
    ax_clear_all = plt.axes([left, current_y - row_height, width, row_height])
    btn_clear_all = Button(ax_clear_all, lang.t(*TEXTS['clear_all']),
                           color='lightcoral', hovercolor='red')
    btn_clear_all.on_clicked(clear_all_points)
    panel_widgets.append(btn_clear_all)

    # 语言切换按钮
    ax_lang = plt.axes([left, 0.02, width, row_height])
    btn_lang = Button(ax_lang, 'EN/中', color='0.85', hovercolor='0.7')

    def switch_language(event):
        lang.set_language('en' if lang.current_lang == 'zh' else 'zh')
        show_control_panel()
        update_plot()

    btn_lang.on_clicked(switch_language)
    panel_widgets.append(btn_lang)

    update_file_list()
    plt.draw()


def toggle_panel(event):
    global panel_visible
    panel_visible = not panel_visible
    if panel_visible:
        show_control_panel()
        menu_button.label.set_text(lang.t(*TEXTS['panel_expand']))
    else:
        clear_panel()
        menu_button.label.set_text(lang.t(*TEXTS['panel_collapse']))
    plt.draw()


# 主菜单按钮
menu_button = Button(plt.axes([0.82, 0.9, 0.15, 0.05]),
                     lang.t(*TEXTS['panel_collapse']),
                     color='lightgray', hovercolor='silver')
menu_button.on_clicked(toggle_panel)

plt.show()