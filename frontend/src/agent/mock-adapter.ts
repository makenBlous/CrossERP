import type { AgentAdapter, AgentPageContext, AgentPart } from '@/agent/adapter'
import { projectDashboard, projectIssues, projectOrder, projectProfit } from '@/mocks/project'
import { useMockDbStore } from '@/stores/mockdb'
import { formatMoney } from '@/utils/format'

function wait(ms: number) {
  return new Promise<void>(resolve => {
    setTimeout(resolve, ms)
  })
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

    await emitText(
      zh
        ? `当前页面是「${context.pageName}」。我只读取演示数据里已经算好的结果，不会重算或改账。`
        : `This page is “${context.pageName}”. I only read stored demo results and will not recalculate or post.`,
      emit,
    )

    if (context.selectedId) {
      const order = projectOrder(db, context.selectedId)

      if (order) {
        emit({
          kind: 'card',
          card: {
            kind: 'query',
            title: zh ? '只读订单' : 'Read-only order',
            lines: [
              { label: zh ? '单号' : 'Order', value: order.orderNo },
              { label: zh ? '状态' : 'Status', value: order.status },
              { label: zh ? '净额' : 'Net', value: formatMoney(order.net, order.currency) },
            ],
          },
        })
      }
    }

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

    if (/建议|审批|suggest|approval/.test(ask)) {
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
              title: zh ? `处理异常 ${issue.id}` : `Handle ${issue.id}`,
              summary: zh
                ? `沿用已存储差额 ${formatMoney(issue.amount, issue.currency)}。不重算，不写账。`
                : `Uses the stored difference ${formatMoney(issue.amount, issue.currency)}. No recalculation, no posting.`,
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
