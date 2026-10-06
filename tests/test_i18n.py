from io import BytesIO
import warnings
import numpy as np
from cet import charts
from cet.core import Component, presets
from cet.i18n import translate


def test_chinese_charts_have_labels_and_render_without_missing_glyphs():
    fmt = presets()["Medium format 48 × 36"]
    figures = [charts.format_rectangles([fmt], language="zh"),
               charts.fov_plot(fmt, 80, language="zh"),
               charts.coverage_plot(fmt, 80, 1, 2, language="zh"),
               charts.stack_plot([Component("测试转接环", 70)], 70, language="zh"),
               charts.histogram(np.linspace(-.1, .1, 100), -.05, .05, language="zh")]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for fig in figures:
            assert any('\u4e00' <= c <= '\u9fff' for c in fig.axes[0].get_xlabel())
            charts.prepare_font(fig)
            fig.savefig(BytesIO(), format="png")
            fig.clear()
    assert not any("Glyph" in str(w.message) for w in caught)


def test_presets_and_validation_are_translated():
    for fmt in presets().values():
        assert translate(fmt.note, "zh") != fmt.note
    assert translate("Samples must be an integer from 100 to 250,000.", "zh") == "样本数必须为 100 至 250,000 之间的整数。"
    assert translate("Complete every field in component row 4, or delete that row.", "zh") == "请填写零件表第 4 行的所有字段，或删除该行。"
    assert translate("+1.234 stops", "zh") == "+1.234 档"
