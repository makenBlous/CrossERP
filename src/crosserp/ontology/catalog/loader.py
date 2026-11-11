"""实体目录资源加载、规范化和启动时契约校验。"""

# 设计附件的风险文本保留原始中文标点和历史编码，不能改写资源内容。
# ruff: noqa: RUF001,RUF002,RUF003

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

_ACTION_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)\b")
_RISK_MAP = {
    "无（只读）": "none",
    "低（自动执行；不改业务数据或只做只读结果）": "low",
    "中（自动执行；可撤销；不设次数限制；中风险只记每日一条站内摘要）": "medium",
    "高（agent 可发起；人工审批或本人确认后才生效）": "high",
    "高（agent 可发起；人工审批后才生效）": "high",
    "危险（agent 禁止）": "critical",
}


@dataclass(frozen=True)
class ActionTypeDef:
    id: str
    entity: str
    kind: str
    summary: str
    permission: str
    risk_tier: str
    ai_callable: bool
    ai_max_autonomy: str
    emits: tuple[str, ...]
    projections: tuple[str, ...]
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        result = dict(self.raw)
        result.update(
            {
                "id": self.id,
                "entity": self.entity,
                "riskTier": self.risk_tier,
                "aiCallable": self.ai_callable,
                "aiMaxAutonomy": self.ai_max_autonomy,
            }
        )
        return result


@dataclass(frozen=True)
class EntityTypeDef:
    id: str
    name_zh: str
    module: str
    kind: str
    properties: tuple[str, ...]
    relations: tuple[str, ...]
    state_machine: dict[str, Any] | None
    actions: tuple[ActionTypeDef, ...]
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        result = dict(self.raw)
        result["actions"] = [action.as_dict() for action in self.actions]
        return result


@dataclass(frozen=True)
class EventTypeDef:
    id: str
    source_action: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "sourceAction": self.source_action}


@dataclass(frozen=True)
class OntologyCatalog:
    version: str
    entity_types: tuple[EntityTypeDef, ...]
    actions: tuple[ActionTypeDef, ...]
    events: tuple[EventTypeDef, ...]

    @property
    def entity_by_id(self) -> dict[str, EntityTypeDef]:
        return {entity.id: entity for entity in self.entity_types}

    @property
    def action_by_id(self) -> dict[str, ActionTypeDef]:
        return {action.id: action for action in self.actions}

    @property
    def event_by_id(self) -> dict[str, EventTypeDef]:
        return {event.id: event for event in self.events}


def catalog_path() -> Path:
    """返回包内 YAML 资源路径，便于一致性测试和发行包检查。"""
    return Path(str(files("crosserp.ontology.catalog").joinpath("ontology-entities.yaml")))


def load_catalog(path: Path | str | None = None) -> OntologyCatalog:
    source = Path(path) if path is not None else catalog_path()
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    validate_catalog(payload)
    entities: list[EntityTypeDef] = []
    actions: list[ActionTypeDef] = []
    event_map: dict[str, EventTypeDef] = {}
    for item in payload["entityTypes"]:
        entity_actions: list[ActionTypeDef] = []
        for raw_action in item["actions"]:
            action_id = str(raw_action["id"])
            risk = _RISK_MAP.get(str(raw_action["riskTier"])) if "riskTier" in raw_action else None
            if risk is None:
                risk = _risk_from_autonomy(
                    str(raw_action["aiMaxAutonomy"]),
                    str(raw_action["riskTier"]) if "riskTier" in raw_action else "",
                )
            autonomy = str(raw_action["aiMaxAutonomy"])
            action = ActionTypeDef(
                id=action_id,
                entity=str(item["id"]),
                kind=str(raw_action["kind"]),
                summary=str(raw_action["summary"]),
                permission=str(raw_action["permission"]),
                risk_tier=risk,
                ai_callable=autonomy != "L0",
                ai_max_autonomy=autonomy,
                emits=tuple(str(x) for x in raw_action["emits"]) if "emits" in raw_action else (),
                projections=tuple(str(x) for x in raw_action["projections"])
                if "projections" in raw_action
                else (),
                raw=dict(raw_action),
            )
            entity_actions.append(action)
            actions.append(action)
            for event_id in action.emits:
                event_map.setdefault(event_id, EventTypeDef(event_id, action.id))
        entities.append(
            EntityTypeDef(
                id=str(item["id"]),
                name_zh=str(item["nameZh"]),
                module=str(item["module"]),
                kind=str(item["kind"]),
                properties=tuple(str(x) for x in item["properties"]),
                relations=tuple(str(x) for x in item["relations"]),
                state_machine=item["stateMachine"] if "stateMachine" in item else None,
                actions=tuple(entity_actions),
                raw=dict(item),
            )
        )
    return OntologyCatalog(
        version=str(payload["version"]),
        entity_types=tuple(entities),
        actions=tuple(actions),
        events=tuple(event_map.values()),
    )


def validate_catalog(payload: dict[str, Any]) -> None:
    """校验目录结构、动作元数据和状态迁移引用。"""
    entities = payload["entityTypes"]
    if not isinstance(entities, list) or not entities:
        raise ValueError("ontology catalog entityTypes 不能为空")
    entity_ids = {str(item["id"]) for item in entities}
    action_ids: set[str] = set()
    for entity in entities:
        entity_id = str(entity["id"])
        if not entity_id or entity_id == "None":
            raise ValueError("entity type 缺少 id")
        for action in entity["actions"]:
            action_id = str(action["id"])
            if action_id in action_ids:
                raise ValueError(f"重复 action: {action_id}")
            if not action_id.startswith(entity_id + "."):
                raise ValueError(f"action 不属于实体: {action_id}")
            if not action["permission"]:
                raise ValueError(f"action 缺少 permission: {action_id}")
            if not action["riskTier"] and not action["aiMaxAutonomy"]:
                raise ValueError(f"action 缺少风险档: {action_id}")
            action_ids.add(action_id)
    for entity in entities:
        entity_id = str(entity["id"])
        state_machine = entity["stateMachine"] if "stateMachine" in entity else None
        if state_machine is None:
            continue
        for transition in state_machine["transitions"]:
            references = [".".join(match) for match in _ACTION_RE.findall(str(transition))]
            explicit = [ref for ref in references if ref in action_ids]
            if explicit:
                continue
            own_references = [ref for ref in references if ref.startswith(entity_id + ".")]
            if own_references:
                raise ValueError(f"state transition 缺少对应 action: {entity_id}: {transition}")
            # 目录允许系统定时器/后台任务推进状态；其动作由系统调度器实现。
            # 其他实体动作（如 Approval.decide/IngestBatch.project）由对应实体负责。
    unknown_entities = [action_id.split(".", 1)[0] for action_id in action_ids if "." in action_id]
    if any(entity_id not in entity_ids for entity_id in unknown_entities):
        raise ValueError("action 引用了不存在的实体")


def _risk_from_autonomy(autonomy: str, risk_text: str = "") -> str:
    if autonomy == "L1":
        return "none"
    if autonomy == "L2":
        return "high"
    if autonomy == "L3":
        # 设计附件在当前工作树中有少量历史编码损坏，仍保留可判定的等级首字。
        if risk_text.startswith("�У"):
            return "medium"
        if risk_text.startswith("�ͣ"):
            return "low"
        return "critical"
    return "critical"


__all__ = [
    "ActionTypeDef",
    "EntityTypeDef",
    "EventTypeDef",
    "OntologyCatalog",
    "catalog_path",
    "load_catalog",
    "validate_catalog",
]
