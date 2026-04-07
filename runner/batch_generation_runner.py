# 文件名：runner/batch_generation_runner.py
# 说明：批量生成入口V3（Matrix模式 + Summary标准化）
# 定位：组织调用，复用现有能力，不重写逻辑
# 改造：添加matrix开关, 保持normal模式完全不变, summary结构标准化

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runner.frame_preview_runner import process_single_item, render_style_preview, DEFAULT_TITLE, DEFAULT_HIGHLIGHT

OUTPUT_DIR = PROJECT_ROOT / "output" / "batch_generation"

# 冻结的5个style列表（顺序固定，用于matrix循环）
ALL_STYLES = [
    "creator_clean",
    "product_focus",
    "life_story",
    "ai_control_lab",
    "personal_ip",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch generation runner V2: process multiple inputs with optional matrix mode."
    )
    parser.add_argument(
        "--input-text",
        action="append",
        default=None,
        help="Input text items (can be specified multiple times)."
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Input file with one item per line."
    )
    parser.add_argument(
        "--style",
        type=str,
        default=None,
        help="Manually specify a single style for all items (highest priority)."
    )
    parser.add_argument(
        "--disable-ai",
        action="store_true",
        default=False,
        help="Disable AI generation for all items."
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        default=False,
        help="Enable matrix mode: each input generated with all 5 styles (N×5 results)."
    )
    return parser.parse_args()


def load_input_texts(input_text_list: List[str] | None, input_file: str | None) -> List[str]:
    """
    加载输入文本
    
    优先级：
    1. CLI --input-text参数列表
    2. 文件 --input-file
    
    返回：输入文本列表
    """
    texts = []
    
    # 方式1：CLI参数
    if input_text_list:
        texts.extend(input_text_list)
    
    # 方式2：文件
    if input_file:
        file_path = Path(input_file)
        if not file_path.exists():
            print(f"[BATCH] Warning: input file not found: {file_path}")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:  # 跳过空行
                        texts.append(line)
    
    return texts


def _build_contract_paths(
    item_index: int,
    style_name: str,
    is_matrix: bool,
    output_base_dir: Path = None,
) -> Dict[str, Path]:
    """
    统一生成 output contract 路径。
    
    参数：
        item_index: item 序号
        style_name: style 名称
        is_matrix: 是否 matrix 模式
        output_base_dir: 输出 base 目录
    
    返回：
        {
            "output_dir": Path,
            "preview_path": Path,
            "meta_path": Path,
        }
    """
    if output_base_dir is None:
        output_base_dir = OUTPUT_DIR
    
    # 构造 output_dir
    if is_matrix:
        output_dir = output_base_dir / f"item_{item_index:03d}" / style_name
    else:
        output_dir = output_base_dir / f"item_{item_index:03d}"
    
    preview_path = output_dir / "preview.png"
    meta_path = output_dir / "meta.json"
    
    return {
        "output_dir": output_dir,
        "preview_path": preview_path,
        "meta_path": meta_path,
    }


def _validate_meta_json(meta_path: Path) -> bool:
    """
    验证 meta.json 是否存在且可解析。
    
    返回：
        True: meta.json 存在且是合法 JSON
        False: meta.json 不存在或非法 JSON
    """
    if not meta_path.exists():
        return False
    
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, Exception):
        return False


def _validate_output_contract(
    contracts: Dict[str, Path],
    status_before: str,
) -> tuple[str, str | None]:
    """
    验证 output contract，根据结果调整 status 和 error。
    
    参数：
        contracts: 路径合约 dict (from _build_contract_paths)
        status_before: 执行前的 status ("success" 或 "failed")
    
    返回：
        (adjusted_status, error_msg)
        
        如果 status_before="success"，但文件缺失或 meta.json 非法，
        则改判为 failed，并包含错误信息。
        
        如果 status_before="failed"，保持 failed，不做额外检查。
    """
    if status_before == "failed":
        # 失败场景：不要求文件存在，但路径必须可预期（已由合约保证）
        return "failed", None
    
    # success 场景：两个文件都必须存在且可读
    preview_path = contracts["preview_path"]
    meta_path = contracts["meta_path"]
    
    # 检查 preview.png
    if not preview_path.exists():
        return "failed", "missing preview file after successful run"
    
    # 检查 meta.json 存在性和可解析性
    if not _validate_meta_json(meta_path):
        if not meta_path.exists():
            return "failed", "missing meta file after successful run"
        else:
            return "failed", "meta.json is not valid JSON"
    
    # 所有检查通过
    return "success", None


def process_single_batch_item(
    input_text: str,
    item_index: int,
    manual_style: str | None = None,
    enable_ai: bool = True,
    output_base_dir: Path = None,
    matrix_mode: bool = False,
    target_style: str | None = None,  # 在matrix模式下指定的style
) -> dict:
    """
    处理单条item的核心逻辑（带output contract校验）
    
    参数：
        input_text: 输入文本
        item_index: item序号（用于目录命名）
        manual_style: 手动指定的style（normal模式下）
        enable_ai: 是否启用AI生成
        output_base_dir: 输出base目录
        matrix_mode: 是否matrix模式
        target_style: matrix模式下的目标style
    
    返回：item meta信息（含output contract结果）
    """
    if output_base_dir is None:
        output_base_dir = OUTPUT_DIR
    
    # ===== 第1步：统一通过合约生成路径 =====
    contracts = _build_contract_paths(
        item_index=item_index,
        style_name=target_style or "unknown",
        is_matrix=matrix_mode,
        output_base_dir=output_base_dir,
    )
    
    output_dir = contracts["output_dir"]
    preview_path = contracts["preview_path"]
    meta_path = contracts["meta_path"]
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    meta = {
        "index": item_index,
        "input_text": input_text[:100],
    }
    
    try:
        # ===== 第2步：执行生成 =====
        if matrix_mode and target_style:
            result = process_single_item(
                input_text=input_text,
                style_name=target_style,
                title=None,
                highlight=None,
                enable_ai=enable_ai,
            )
        else:
            result = process_single_item(
                input_text=input_text,
                style_name=manual_style,
                title=None,
                highlight=None,
                enable_ai=enable_ai,
            )
        
        # 更新meta
        meta.update({
            "style_name": result["style_name"],
            "title": result["title"],
            "highlight": result["highlight"],
            "used_auto_style": result["used_auto_style"],
            "used_ai_generation": result["used_ai_generation"],
        })
        
        # ===== 第3步：渲染预览 =====
        render_style_preview(
            style_name=result["style_name"],
            title=result["title"],
            highlight=result["highlight"],
            output_path=preview_path,
        )
        
        meta["status"] = "success"
        
    except Exception as e:
        meta["status"] = "failed"
        meta["error"] = str(e)
    
    # ===== 第4步：保存meta.json（无论成功失败都要保存） =====
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # meta.json保存失败也会被后续contract校验检出
        pass
    
    # ===== 第5步：output contract校验 =====
    # 这一步会根据文件实际存在性和可读性调整 status/error
    adjusted_status, contract_error = _validate_output_contract(
        contracts=contracts,
        status_before=meta.get("status", "failed"),
    )
    
    if adjusted_status != meta.get("status"):
        # status被调整（从success改为failed），说明contract violation
        meta["status"] = adjusted_status
        if contract_error:
            meta["error"] = contract_error
            # 日志：仅在contract失败时打印，不要噪音
            print(f"[ContractFail] item_{item_index:03d} / {result.get('style_name', '?')} / {contract_error}")
    
    return meta


def process_batch_normal(
    input_texts: List[str],
    manual_style: str | None = None,
    enable_ai: bool = True,
) -> tuple[List[dict], int, int]:
    """
    Normal模式：处理批量输入（保持现有行为完全不变）
    
    返回：(items列表, 成功数, 失败数)
    """
    items = []
    success_count = 0
    failed_count = 0
    
    for index, input_text in enumerate(input_texts, start=1):
        meta = process_single_batch_item(
            input_text=input_text,
            item_index=index,
            manual_style=manual_style,
            enable_ai=enable_ai,
            output_base_dir=OUTPUT_DIR,
            matrix_mode=False,
            target_style=None,
        )
        
        if meta.get("status") == "success":
            success_count += 1
            print(f"[BATCH] item_{index:03d}: OK - {meta['style_name']}")
        else:
            failed_count += 1
            print(f"[BATCH] item_{index:03d}: FAIL - {meta.get('error', 'Unknown error')}")
        
        items.append(meta)
    
    return items, success_count, failed_count


def process_batch_matrix(
    input_texts: List[str],
    manual_style: str | None = None,
    enable_ai: bool = True,
) -> tuple[List[List[dict]], int, int, int]:
    """
    Matrix模式：每条input按全部style执行
    
    返回：(items_by_style二维列表, 总成功数, 总失败数, 总任务数)
    """
    all_items = []
    total_success = 0
    total_failed = 0
    total_jobs = len(input_texts) * len(ALL_STYLES)
    
    for input_idx, input_text in enumerate(input_texts, start=1):
        input_items = []
        
        for style_idx, style_name in enumerate(ALL_STYLES, start=1):
            # 日志输出
            print(f"[MATRIX] item {input_idx}/{len(input_texts)} | style {style_idx}/{len(ALL_STYLES)} | {style_name}")
            
            meta = process_single_batch_item(
                input_text=input_text,
                item_index=input_idx,
                manual_style=None,  # matrix模式下不用manual_style
                enable_ai=enable_ai,
                output_base_dir=OUTPUT_DIR,
                matrix_mode=True,
                target_style=style_name,  # 强制指定style
            )
            
            if meta.get("status") == "success":
                total_success += 1
                print(f"  [OK] {style_name}")
            else:
                total_failed += 1
                print(f"  [FAIL] {style_name}")
            
            input_items.append(meta)
        
        all_items.append(input_items)
    
    return all_items, total_success, total_failed, total_jobs


def _determine_item_status(styles_results: List[dict]) -> str:
    """根据所有style的结果，决定item的status。
    
    - success: 所有style都成功
    - failed: 所有style都失败
    - partial: 部分成功部分失败
    """
    if not styles_results:
        return "failed"
    
    success_count = sum(1 for s in styles_results if s.get("status") == "success")
    total_count = len(styles_results)
    
    if success_count == total_count:
        return "success"
    elif success_count == 0:
        return "failed"
    else:
        return "partial"


def _build_style_result(meta: dict, item_index: int, is_matrix: bool) -> dict:
    """从process_single_batch_item返回的meta构建标准化的style结果对象。
    
    使用统一的contract路径生成逻辑。
    
    参数：
        meta: process_single_batch_item返回的meta dict
        item_index: item序号（用于构造路径）
        is_matrix: 是否matrix模式（影响output_dir结构）
    
    返回：标准化的style结果对象
    """
    style_name = meta.get("style_name", "unknown")
    status = meta.get("status", "failed")
    error = meta.get("error") if status == "failed" else None
    
    # ===== 使用统一合约生成路径 =====
    contracts = _build_contract_paths(
        item_index=item_index,
        style_name=style_name,
        is_matrix=is_matrix,
        output_base_dir=OUTPUT_DIR,
    )
    
    return {
        "style": style_name,
        "status": status,
        "output_dir": str(contracts["output_dir"].relative_to(PROJECT_ROOT)),
        "preview_path": str(contracts["preview_path"].relative_to(PROJECT_ROOT)),
        "meta_path": str(contracts["meta_path"].relative_to(PROJECT_ROOT)),
        "error": error,
    }


def _build_item_result(item_index: int, input_text: str, styles_results: List[dict]) -> dict:
    """从styles_results构建标准化的item对象。"""
    return {
        "item_id": f"item_{item_index:03d}",
        "input_index": item_index,
        "input_text": input_text[:100],
        "status": _determine_item_status(styles_results),
        "styles": styles_results,
    }


def _get_generated_at() -> str:
    """获取当前时间戳（ISO 8601格式）。"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def generate_batch_summary_normal(items: List[dict], success_count: int, failed_count: int) -> dict:
    """生成normal模式的标准化batch_summary。
    
    normal模式特点：
    - mode="normal"
    - total_styles=1
    - total_jobs=total_inputs
    - 每个item的styles数组长度=1（单个auto-selected style）
    
    参数：
        items: process_batch_normal返回的meta列表
        success_count: 成功的job数
        failed_count: 失败的job数
    
    返回：标准化summary dict
    """
    total_inputs = len(items)
    total_styles = 1
    total_jobs = total_inputs * total_styles
    
    # 构建items结构
    items_result = []
    for item_meta in items:
        item_index = item_meta.get("index", 0)
        input_text = item_meta.get("input_text", "")
        
        # 为这个item构建单个style结果
        style_result = _build_style_result(item_meta, item_index, is_matrix=False)
        
        # 构建item对象
        item_obj = _build_item_result(item_index, input_text, [style_result])
        items_result.append(item_obj)
    
    return {
        "mode": "normal",
        "total_inputs": total_inputs,
        "total_styles": total_styles,
        "total_jobs": total_jobs,
        "success_count": success_count,
        "failed_count": failed_count,
        "output_root": str(OUTPUT_DIR.relative_to(PROJECT_ROOT)),
        "generated_at": _get_generated_at(),
        "items": items_result,
    }


def generate_batch_summary_matrix(
    all_items: List[List[dict]],
    total_success: int,
    total_failed: int,
    total_jobs: int,
) -> dict:
    """生成matrix模式的标准化batch_summary。
    
    matrix模式特点：
    - mode="matrix"
    - total_styles=5
    - total_jobs=total_inputs × total_styles
    - 每个item的styles数组长度=5（所有固定style）
    
    参数：
        all_items: process_batch_matrix返回的二维meta列表（List[List[meta]]）
        total_success: 成功的job数
        total_failed: 失败的job数
        total_jobs: 总job数
    
    返回：标准化summary dict
    """
    total_inputs = len(all_items)
    total_styles = len(ALL_STYLES)
    
    # 构建items结构
    items_result = []
    for item_index, input_items_metas in enumerate(all_items, start=1):
        input_text = input_items_metas[0].get("input_text", "") if input_items_metas else ""
        
        # 为这个item的所有styles构建结果
        styles_results = []
        for style_meta in input_items_metas:
            style_result = _build_style_result(style_meta, item_index, is_matrix=True)
            styles_results.append(style_result)
        
        # 构建item对象
        item_obj = _build_item_result(item_index, input_text, styles_results)
        items_result.append(item_obj)
    
    return {
        "mode": "matrix",
        "total_inputs": total_inputs,
        "total_styles": total_styles,
        "total_jobs": total_jobs,
        "success_count": total_success,
        "failed_count": total_failed,
        "output_root": str(OUTPUT_DIR.relative_to(PROJECT_ROOT)),
        "generated_at": _get_generated_at(),
        "items": items_result,
    }



def main() -> None:
    args = parse_args()
    
    # 加载输入
    input_texts = load_input_texts(args.input_text, args.input_file)
    
    if not input_texts:
        print("[BATCH] Error: No input provided.")
        print("Usage:")
        print("  python runner/batch_generation_runner.py --input-text 'text1' --input-text 'text2'")
        print("  python runner/batch_generation_runner.py --input-file data/batch_inputs.txt")
        print("  python runner/batch_generation_runner.py --input-file data/batch_inputs.txt --matrix")
        sys.exit(1)
    
    mode = "matrix" if args.matrix else "normal"
    print(f"[BATCH] ========== Batch Generation Started (Mode: {mode.upper()}) ==========")
    print(f"[BATCH] Total inputs: {len(input_texts)}")
    print(f"[BATCH] Manual style: {args.style or 'auto-select'}")
    print(f"[BATCH] AI enabled: {not args.disable_ai}")
    print(f"[BATCH] Output dir: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    print()
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 执行批量处理
    if args.matrix:
        # ===== Matrix 模式 =====
        all_items, total_success, total_failed, total_jobs = process_batch_matrix(
            input_texts=input_texts,
            manual_style=args.style,
            enable_ai=not args.disable_ai,
        )
        
        print()
        
        # 生成总表
        summary = generate_batch_summary_matrix(all_items, total_success, total_failed, total_jobs)
    else:
        # ===== Normal 模式（保持原有行为） =====
        items, total_success, total_failed = process_batch_normal(
            input_texts=input_texts,
            manual_style=args.style,
            enable_ai=not args.disable_ai,
        )
        
        print()
        
        # 生成总表
        summary = generate_batch_summary_normal(items, total_success, total_failed)
    
    # 保存summary
    summary_path = OUTPUT_DIR / "batch_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"[BATCH] ========== Batch Generation Completed ==========")
    print(f"[BATCH] Mode: {mode.upper()}")
    print(f"[BATCH] Total: {summary['total_jobs']} | Success: {summary['success_count']} | Failed: {summary['failed_count']}")
    print(f"[BATCH] Summary: {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"[BATCH] Output: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
