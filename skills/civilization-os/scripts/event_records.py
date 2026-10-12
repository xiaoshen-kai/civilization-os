#!/usr/bin/env python3
"""Deterministic event cards from minimal official-source snapshots; no network."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "fdic": {"start": 101, "count": 300, "source": "R-FDIC", "domain": "finance"},
    "cfpb": {"start": 401, "count": 200, "source": "R-CFPB", "domain": "regulatory_action"},
    "clinical": {"start": 601, "count": 250, "source": "R-CTG", "domain": "clinical_research"},
    "nobel": {"start": 851, "count": 150, "source": "R-NOBEL", "domain": "scientific_awards"},
}
CHECKED_ON = "2026-10-12"

def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"

def format_number(value):
    if value is None:
        return "未提供"
    return str(value)

def render_record(dataset, record, case_id, snapshot_hash):
    f = record["fields"]
    source_id = DATASETS[dataset]["source"]
    key = record["record_key"]
    if dataset == "fdic":
        event_time = datetime.strptime(f["FAILDATE"], "%m/%d/%Y").date().isoformat()
        title = f"FDIC 失败记录：{f['NAME']}（{event_time}）"
        facts = [
            f"FDIC 将 {f['NAME']}（{f['CITY']}，{f['PSTALP']}）列为 FAILURE，生效日期字段为 {event_time}，记录 ID 为 {f['ID']}。",
            f"生效日前最后申报的资产 QBFASSET 为 {format_number(f['QBFASSET'])}，存款 QBFDEP 为 {format_number(f['QBFDEP'])}；两项单位均为千美元，缺值不能当作 0。"
        ]
        locators = ["fields.ID, NAME, CITY, PSTALP, RESTYPE, FAILDATE",
                    "fields.QBFASSET, QBFDEP; FDIC failure_properties.yaml field definitions"]
        models = ["P094"]
        keywords = ["银行", "失败", "FDIC", "风险", f["NAME"], event_time]
        limit = "官方数据库支持失败类型、日期和申报财务字段；不提供本卡的失败原因、管理者决策或反事实。金额不是失败日估值，样本不能用于估计失败概率。"
        mapping = "P094 只用于提出损失承受力与生存约束的问题；这条记录本身不验证某种失败机制。"
        strength = "direct"
        confidence = "high"
    elif dataset == "cfpb":
        event_time = f["date_filed"]
        title = f"CFPB 执法索引：{f['title']}（{event_time}）"
        facts = [f"CFPB 执法目录列出“{f['title']}”，Date filed 为 {event_time}，条目链接为 {record['record_url']}。"]
        locators = ["fields.title, date_filed, url, index_page; article h3 and time[datetime]"]
        models = ["P077", "P098"]
        keywords = ["CFPB", "消费者", "执法", "监管", f["title"], event_time]
        limit = "只核对官方目录条目与 Date filed；未逐条审阅这 200 项诉状、命令及后来状态。列入目录不等于指控成立、付款完成或命令仍有效；不得由索引推断因果。"
        mapping = "P077 用于提出信息与披露问题，P098 用于安排进一步核验；索引未证实这些机制发生。"
        strength = "direct"
        confidence = "high"
    elif dataset == "clinical":
        posted = f["results_first_post_date_struct"]
        event_time = posted["date"]
        title = f"临床结果记录：{f['nct_id']} -- {f['brief_title']}"
        measurement = f["measurements"][0]
        group = next(g for g in f["groups"] if g["id"] == measurement["groupId"])
        qualifier = "；日期类型为 ESTIMATED，保留来源的不确定性" if posted.get("type") == "ESTIMATED" else ""
        label = " / ".join(str(x) for x in (measurement.get("class_title"),measurement.get("category_title")) if x)
        label = label or "原始未命名单元"
        facts = [
            f"登记记录 {f['nct_id']} 的 allocation 为 {f['allocation']}，当前快照状态为 {f['overall_status']}；首次提交结果日期为 {f['results_first_submit_date']}，首次公开结果日期为 {event_time}（{posted.get('type', '未提供')}）{qualifier}。",
            f"首个有测量结果的主要终点为“{f['primary_title']}”，时间窗为 {f['time_frame']}，参数类型为 {f['param_type']}，单位为 {f['unit_of_measure']}，离散类型为 {f.get('dispersion_type') or '未提供'}。",
            f"保留的首个结果单元：组“{group['title']}”（{group['id']}），分类“{label}”，value 为 {measurement['value']}。原始分析单位为 {f.get('type_units_analyzed') or '未提供'}，选定分母单位为 {f.get('denom_units_selected') or '未提供'}。该单元不是完整组间比较；分母数值、其余单元及离散程度须读取快照。"
        ]
        locators = [
            "fields.nct_id, allocation, overall_status, results_first_submit_date, results_first_post_date_struct",
            "fields.primary_index, primary_title, time_frame, param_type, unit_of_measure, dispersion_type",
            "fields.groups, denoms, measurements[0], type_units_analyzed, denom_units_selected; raw primary_index/class_index/category_index/measurement_index"
        ]
        models = ["P050", "P098"]
        keywords = ["临床", "随机", "结果", "ClinicalTrials.gov", f["nct_id"], f["brief_title"], *f["conditions"]]
        limit = "研究登记与结果由申办者或研究者申报，政府收录不等于认可准确性或疗效。只保留一个主要终点及最多 4 个结果单元；未核查偏倚、预注册变更、完整分析和临床意义，不形成医疗建议。首次公开不等于完成研究日期；ESTIMATED 不得改成 ACTUAL。"
        mapping = "P050、P098 用于学习如何检查分配、终点、分母与完整分析；不能由登记为随机研究就宣称本卡已证明疗效。"
        strength = "reported"
        confidence = "medium"
    elif dataset == "nobel":
        event_time = f["award_year"]
        category = {"phy":"物理学","che":"化学","med":"生理学或医学"}[f["category_code"]]
        names = "；".join(x["name"] for x in f["laureates"])
        motivations = list(dict.fromkeys(x["motivation"] for x in f["laureates"]))
        title = f"诺贝尔科研记录：{event_time} 年 {category}"
        facts = [
            f"诺贝尔官方 API 在 {event_time} 年 {category} 条目列出 {names}；同一年度类别的全部获奖者合并为一条案例。",
            "官方授奖说明保留于快照：" + " | ".join(motivations)
        ]
        locators = ["fields.award_year, category, laureates[*].id/name/portion",
                    "fields.laureates[*].motivation"]
        models = ["P098"]
        keywords = ["诺贝尔奖", category, event_time, *[x["name"] for x in f["laureates"]], *motivations]
        limit = "官方记录支持获奖年度、类别、名单与授奖说明；奖项不是结果复现、完整论文审查或跨领域因果证明。每类分年抽取 50 项，不构成完整获奖者数据库，也不包含菲尔兹奖案例库。"
        mapping = "P098 用于沿授奖主题寻找原始研究与可检验方法；获奖荣誉本身不验证模型迁移。"
        strength = "direct"
        confidence = "high"
    else:
        raise ValueError("Unknown dataset")
    claims = [{"claim_id":f"{case_id}.{n:02d}", "claim":fact, "source_ids":[source_id],
               "locator":f"record_key={key}; {locator}", "evidence_strength":strength,
               "causal_limit":limit} for n,(fact,locator) in enumerate(zip(facts,locators),1)]
    return {
        "id":case_id, "record_type":"evidence_event",
        "event_key":dataset+":"+key, "title":title, "event_time":event_time,
        "domain":DATASETS[dataset]["domain"], "result_type":"documented_event",
        "facts":facts, "model_ids":models, "model_mapping_note":mapping,
        "claims":claims, "source_ids":[source_id],
        "keywords":list(dict.fromkeys(x for x in keywords if isinstance(x,str) and x)),
        "provenance":{"source_id":source_id, "row_key":key,
                      "locator":f"event-data/{dataset}.json: records[record_key={key}].fields",
                      "record_url":record["record_url"],
                      "snapshot_file":f"event-data/{dataset}.json",
                      "snapshot_sha256":snapshot_hash},
        "verification":{"status":"checked", "checked_on":CHECKED_ON,
                        "fact_confidence":confidence, "causal_confidence":"low",
                        "independent_source_groups":1, "limitations":limit}
    }

def render_dataset(dataset, root=ROOT):
    path = root/"references"/"event-data"/(dataset+".json")
    snapshot_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    snapshot = json.loads(path.read_text(encoding="utf-8-sig"))
    if snapshot["dataset"] != dataset or snapshot["source_id"] != DATASETS[dataset]["source"]:
        raise ValueError(f"{dataset}: mismatched dataset or source")
    records = snapshot["records"]
    if len(records) != DATASETS[dataset]["count"]:
        raise ValueError(f"{dataset}: unexpected record count")
    keys = [x["record_key"] for x in records]
    if len(set(keys)) != len(keys):
        raise ValueError(f"{dataset}: duplicate row key")
    start = DATASETS[dataset]["start"]
    return [render_record(dataset,r,f"C{start+n:03d}",snapshot_hash) for n,r in enumerate(records)]

def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true",help="Explicitly regenerate the four derived cases-events-*.json files.")
    args=parser.parse_args()
    errors=[]
    for dataset in DATASETS:
        expected=json_text(render_dataset(dataset))
        path=ROOT/"references"/f"cases-events-{dataset}.json"
        if args.write:
            path.write_text(expected,encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8-sig") != expected:
            errors.append(f"{dataset}: derived case file differs from selected snapshot")
    if errors:
        print("\n".join(errors))
        return 1
    print("900 event records: " + ("regenerated" if args.write else "snapshot rendering matches") + ". This checks consistency, not independent causal validity.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
