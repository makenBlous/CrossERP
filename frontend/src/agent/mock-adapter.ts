import type { AgentAdapter, AgentPageContext, AgentPart } from '@/agent/adapter'
import { currentActor } from '@/api/mock-client'
import { projectSkuDetail } from '@/mocks/project-ops'
import { projectDashboard, projectIssues, projectOrder, projectProfit } from '@/mocks/project'
import { listGapDRecords } from '@/mocks/services/gap-d'
import { useMockDbStore } from '@/stores/mockdb'
import { formatMoney } from '@/utils/format'

function wait(ms: number) {
  return new Promise<void>(resolve => {
    setTimeout(resolve, ms)
  })
}

async function answerSelected(
  db: ReturnType<typeof useMockDbStore>['db'],
  id: string,
  ask: string,
  zh: boolean,
  emit: (part: AgentPart) => void,
) {
  const order = projectOrder(db, id)

  if (order) {
    emit({
      kind: 'card',
      card: {
        kind: 'query',
        title: zh ? '只读订单' : 'Read-only order',
        lines: [
          { label: zh ? '单号' : 'Order', value: order.orderNo },
          { label: zh ? '状态' : 'Status', value: order.status },
          { label: zh ? '发货时间' : 'Shipped', value: order.shipment.shippedAt },
          { label: zh ? '物流单号' : 'Tracking', value: order.shipment.trackingNo },
          { label: zh ? '净额' : 'Net', value: formatMoney(order.net, order.currency) },
        ],
      },
    })
    if (/发货|到货|什么时候|when|ship/.test(ask)) {
      await emitText(
        zh
          ? `这张订单的发货时间是 ${order.shipment.shippedAt}，仓库 ${order.shipment.warehouse}，物流单号 ${order.shipment.trackingNo}。`
          : `This order shipped at ${order.shipment.shippedAt} from ${order.shipment.warehouse}. Tracking ${order.shipment.trackingNo}.`,
        emit,
      )
    }

    return
  }

  const sku = projectSkuDetail(db, id)

  if (sku) {
    const latest = sku.costs[sku.costs.length - 1]

    emit({
      kind: 'card',
      card: {
        kind: 'query',
        title: zh ? '只读 SKU' : 'Read-only SKU',
        lines: [
          { label: 'SKU', value: sku.internalSku },
          { label: zh ? '名称' : 'Name', value: sku.title },
          { label: zh ? '当前生效日' : 'Valid from', value: latest?.validFrom ?? '' },
          { label: zh ? '采购成本' : 'Cost', value: latest ? `${latest.unitCost} ${latest.currency}` : '' },
        ],
      },
    })
    if (/成本|生效|cost|when/.test(ask)) {
      const lines = sku.costs.map(item => `${item.validFrom} → ${item.validTo || (zh ? '至今' : 'open')}: ${item.unitCost} ${item.currency}`).join('；')

      await emitText(zh ? `成本时间轴：${lines}` : `Cost timeline: ${lines}`, emit)
    }

    return
  }

  const purchase = db.purchaseOrders.find(item => item.id === id)

  if (purchase) {
    emit({
      kind: 'card',
      card: {
        kind: 'query',
        title: zh ? '只读采购单' : 'Read-only purchase order',
        lines: [
          { label: zh ? '单号' : 'PO', value: purchase.no },
          { label: zh ? '状态' : 'Status', value: purchase.status },
          { label: zh ? '预计到货' : 'Expected arrival', value: purchase.expectedAt.slice(0, 10) },
        ],
      },
    })
    if (/到货|什么时候|when|arriv/.test(ask)) {
      await emitText(
        zh
          ? `这单预计到货日是 ${purchase.expectedAt.slice(0, 10)}。这是单据上已存储的交期，我没有重算。`
          : `The stored expected arrival is ${purchase.expectedAt.slice(0, 10)}. I did not recalculate it.`,
        emit,
      )
    }

    return
  }

  const shipment = db.shipments.find(item => item.id === id)

  if (shipment) {
    const from = db.warehouses.find(item => item.id === shipment.warehouseFrom)?.name ?? shipment.warehouseFrom
    const to = db.warehouses.find(item => item.id === shipment.warehouseTo)?.name ?? shipment.warehouseTo

    emit({
      kind: 'card',
      card: {
        kind: 'query',
        title: zh ? '只读头程' : 'Read-only shipment',
        lines: [
          { label: zh ? '运单' : 'Shipment', value: shipment.no },
          { label: zh ? '状态' : 'Status', value: shipment.status },
          { label: zh ? '发运' : 'Departed', value: shipment.departedAt?.slice(0, 10) || (zh ? '尚未发运' : 'Not departed') },
          { label: zh ? '签收' : 'Arrived', value: shipment.arrivedAt?.slice(0, 10) || (zh ? '尚未签收' : 'Not arrived') },
        ],
      },
    })
    if (/到货|签收|什么时候|when|arriv/.test(ask)) {
      await emitText(
        zh
          ? `这单从 ${from} 到 ${to}。发运日 ${shipment.departedAt?.slice(0, 10) || '尚未发运'}，签收日 ${shipment.arrivedAt?.slice(0, 10) || '尚未签收'}。这些日期来自单据，我没有重算。`
          : `This shipment runs ${from} to ${to}. Departed ${shipment.departedAt?.slice(0, 10) || 'not yet'}, arrived ${shipment.arrivedAt?.slice(0, 10) || 'not yet'}. I did not recalculate the dates.`,
        emit,
      )
    }

    return
  }

  const supplier = db.suppliers.find(item => item.id === id)

  if (supplier) {
    emit({
      kind: 'card',
      card: {
        kind: 'query',
        title: zh ? '只读供应商' : 'Read-only supplier',
        lines: [
          { label: zh ? '名称' : 'Name', value: supplier.name },
          { label: zh ? '国家' : 'Country', value: supplier.country },
          { label: zh ? '币种' : 'Currency', value: supplier.currency },
          { label: zh ? '状态' : 'Status', value: supplier.status },
        ],
      },
    })

    return
  }

  const listing = db.listings.find(item => item.id === id)

  if (listing) {
    const mapped = db.skus.find(item => item.id === listing.skuId)

    emit({
      kind: 'card',
      card: {
        kind: 'query',
        title: zh ? '只读 Listing' : 'Read-only listing',
        lines: [
          { label: zh ? '标题' : 'Title', value: listing.title },
          { label: 'SKU', value: mapped?.internalSku ?? listing.skuId },
          { label: zh ? '状态' : 'Status', value: listing.status },
        ],
      },
    })
  }
}

async function emitText(text: string, emit: (part: AgentPart) => void) {
  const chunks = text.split(/(?<=[。！？])/).filter(Boolean)

  for (const chunk of chunks) {
    await wait(70)
    emit({ kind: 'text', text: chunk })
  }
}

export class MockAgentAdapter implements AgentAdapter {
  async sendMessage(context: AgentPageContext, message: string, emit: (part: AgentPart) => void) {
    const db = useMockDbStore().db
    const ask = message.toLowerCase()
    const zh = context.locale !== 'en'

    if (/工资|薪资|salary|payroll/.test(ask)) {
      const actor = currentActor()
      const ownPayslips = listGapDRecords('HR12', actor)
      const asksForSomeoneElse = /别人|他人|同事|其他员工|another|other employee/.test(ask)

      await emitText(
        asksForSomeoneElse || ownPayslips.length === 0
          ? (zh ? '当前用户只能查询与本人 userId 绑定的工资条，不能查询其他员工工资。' : 'The current user can only query payslips bound to their own userId.')
          : (zh ? `只返回本人 userId 绑定的 ${ownPayslips.length} 条工资条。` : `Only ${ownPayslips.length} payslip(s) bound to the current userId are returned.`),
        emit,
      )

      return
    }

    await emitText(
      zh
        ? `当前页面是「${context.pageName}」。我只读取演示数据里已经算好的结果，不会重算或改账。`
        : `This page is “${context.pageName}”. I only read stored demo results and will not recalculate or post.`,
      emit,
    )

    if (context.selectedId)
      await answerSelected(db, context.selectedId, ask, zh, emit)

    if (/利润|profit/.test(ask)) {
      const row = projectProfit(db).rows[0]
      const dash = projectDashboard(db)
      const lines = [{ label: zh ? '10 月利润' : 'October profit', value: formatMoney(dash.kpi.netProfit, 'USD') }]

      if (row) {
        lines.length = 0
        lines.push({ label: 'SKU', value: row.sku })
        lines.push({ label: zh ? '利润' : 'Profit', value: formatMoney(row.profit, row.currency) })
        lines.push({ label: zh ? '规则' : 'Rule', value: 'demo-rule-1' })
      }

      emit({
        kind: 'card',
        card: {
          kind: 'query',
          title: zh ? '只读利润快照' : 'Stored profit snapshot',
          lines,
        },
      })
    }

    if (/异常|issue|结算/.test(ask)) {
      const issue = projectIssues(db)[0]

      if (issue) {
        emit({
          kind: 'card',
          card: {
            kind: 'query',
            title: zh ? '只读异常' : 'Stored issue',
            lines: [
              { label: zh ? '原因码' : 'Reason', value: issue.code },
              { label: zh ? '金额' : 'Amount', value: formatMoney(issue.amount, issue.currency) },
              { label: zh ? '单号' : 'Ref', value: issue.refNo },
            ],
          },
        })
      }
    }

    if (/建议|审批|suggest|approval|安全库存|退款/.test(ask)) {
      const issue = projectIssues(db)[0]

      if (issue) {
        emit({
          kind: 'card',
          card: {
            kind: 'suggestion',
            title: zh ? '待审批建议' : 'Approval suggestion',
            lines: [
              { label: zh ? '引用' : 'Cites', value: issue.id },
              { label: zh ? '金额' : 'Amount', value: formatMoney(issue.amount, issue.currency) },
            ],
            draft: {
              title: /安全库存|退款/.test(ask)
                ? (zh ? '业务动作待审批建议' : 'Business action approval suggestion')
                : (zh ? `处理异常 ${issue.id}` : `Handle ${issue.id}`),
              summary: zh
                ? /安全库存/.test(ask)
                  ? `已识别 SKU 安全库存调整请求。建议仅进入审批，金额沿用异常快照 ${formatMoney(issue.amount, issue.currency)}，不改库存。`
                  : /退款/.test(ask)
                    ? `已识别退款建议请求。金额引用已存储异常快照 ${formatMoney(issue.amount, issue.currency)}，不直接退款。`
                    : `沿用已存储差额 ${formatMoney(issue.amount, issue.currency)}。不重算，不写账。`
                : `Uses stored values for ${issue.id}. No recalculation or posting.`,
              amount: issue.currency === 'JPY' ? String(issue.amount) : issue.amount.toFixed(4),
              currency: issue.currency,
              storeId: null,
              targetType: 'issue_note',
              targetId: issue.id,
            },
          },
        })
      }
    }
  }
}

export function createAgentAdapter(): AgentAdapter {
  return new MockAgentAdapter()
}
