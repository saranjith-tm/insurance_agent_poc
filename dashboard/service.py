import pandas as pd
from constants import PROGRESS_PCTS


def render_log(log_entries: list) -> str:
    html_lines = []
    for entry in log_entries[-100:]:
        ts = entry.get("timestamp", "")
        level = entry.get("level", "info")
        msg = entry.get("message", "").replace("<", "&lt;").replace(">", "&gt;")
        css_class = f"log-{level}"
        html_lines.append(f'<div class="{css_class}">[{ts}] {msg}</div>')
    return "\n".join(html_lines)


def calculate_step_visual(state_progress, pct_index, running_status):
    pct = PROGRESS_PCTS[pct_index]
    prev_pct = PROGRESS_PCTS[pct_index - 1] if pct_index > 0 else 0
    if state_progress >= pct:
        return {"icon": "✅", "color": "#e8f5e9", "text_color": "#2e7d32"}
    elif state_progress >= prev_pct and running_status:
        return {"icon": "🔄", "color": "#e3f2fd", "text_color": "#1565c0"}
    else:
        return {"icon": "⏸", "color": "#f5f5f5", "text_color": "#9e9e9e"}


def construct_actions_dataframe(actions_taken):
    actions_data = []
    for i, action in enumerate(actions_taken):
        actions_data.append(
            {
                "#": i + 1,
                "Action": action.get("action", "-"),
                "Element": action.get("element_description", "-")[:50],
                "Coordinates": f"({action.get('x', '-')}, {action.get('y', '-')})"
                if action.get("x")
                else "-",
                "Value": str(action.get("text", ""))[:30] or "-",
                "Reasoning": action.get("reasoning", "-")[:60],
            }
        )
    return pd.DataFrame(actions_data)
