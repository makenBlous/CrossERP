<script setup lang="ts">
import { copyGapCRole } from '@/api/gap-c'
import { fetchRoleOverrides, fetchRoles, resetRoleVisibility, saveRoleVisibility } from '@/api/admin'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import { menuGroups, pageCatalog } from '@/config/pages'
import type { DataScopeRuleType } from '@/types/foundation'
import type { Role } from '@/types/domain'

const roles = ref<{ role: string
  label: string }[]>([])

const selected = ref<Role>('operator')

const overrides = ref<{ role: Role
  hiddenGroups: string[]
  hiddenPageIds: string[] }[]>([])

const hiddenGroups = ref<string[]>([])
const hiddenPageIds = ref<string[]>([])
const copyDrawer = ref(false)
const copyName = ref('')
const copyNameEn = ref('')
const copyScope = ref<DataScopeRuleType>('store')
const copyUsers = ref('demo-operator')
const notice = ref('')
const error = ref('')

onMounted(async () => {
  roles.value = (await fetchRoles()).map(item => ({ role: item.role, label: item.label ?? item.role }))
  overrides.value = await fetchRoleOverrides()
  loadRole()
})

function loadRole() {
  const saved = overrides.value.find(item => item.role === selected.value)

  hiddenGroups.value = [...(saved?.hiddenGroups ?? [])]
  hiddenPageIds.value = [...(saved?.hiddenPageIds ?? [])]
}

async function save() {
  if (selected.value === 'admin') {
    hiddenGroups.value = []
    hiddenPageIds.value = []
  }
  await saveRoleVisibility(selected.value, hiddenGroups.value, hiddenPageIds.value)
  overrides.value = await fetchRoleOverrides()
}

async function saveCopy() {
  error.value = ''
  try {
    await copyGapCRole({ sourceRoleId: 'store_operator', nameZh: copyName.value, nameEn: copyNameEn.value || copyName.value, dataScopes: [copyScope.value], memberUserIds: copyUsers.value.split(/[,，]/).map(item => item.trim()).filter(Boolean) })
    notice.value = `角色已复制、保存并模拟指派：${copyName.value}`
    copyDrawer.value = false
    copyName.value = ''
    copyNameEn.value = ''
    copyUsers.value = 'demo-operator'
  }
  catch (cause) {
    error.value = cause instanceof Error ? cause.message : '角色复制失败'
  }
}

async function reset() {
  await resetRoleVisibility(selected.value)
  overrides.value = await fetchRoleOverrides()
  loadRole()
}

function togglePage(id: string) {
  hiddenPageIds.value = hiddenPageIds.value.includes(id) ? hiddenPageIds.value.filter(item => item !== id) : [...hiddenPageIds.value, id]
}
const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div>
    <VAlert
      v-if="notice"
      type="success"
      variant="tonal"
      class="mb-4"
    >
      {{ notice }}；菜单和数据范围会按新角色刷新（静态原型）。
    </VAlert>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-4"
    >
      {{ error }}
    </VAlert>
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h4 class="text-h4">
          角色权限
        </h4><p class="text-body-1 mb-0">
          修改菜单可见性会立即影响左侧导航和直接访问。
        </p>
      </div><div class="d-flex gap-3">
        <VBtn
          variant="tonal"
          @click="copyDrawer = true"
        >
          复制并保存角色
        </VBtn>
        <VBtn
          variant="tonal"
          @click="reset"
        >
          恢复默认
        </VBtn><VBtn
          color="primary"
          @click="save"
        >
          保存权限
        </VBtn>
      </div>
    </div><VRow>
      <VCol
        cols="12"
        md="4"
      >
        <VCard title="角色">
          <VList
            :selected="[selected]"
            mandatory
          >
            <VListItem
              v-for="role in roles"
              :key="role.role"
              :value="role.role"
              @click="selected = role.role as Role; loadRole()"
            >
              <VListItemTitle>{{ role.label }}</VListItemTitle><VListItemSubtitle>{{ role.role }}</VListItemSubtitle>
            </VListItem>
          </VList>
        </VCard>
      </VCol><VCol
        cols="12"
        md="8"
      >
        <VCard title="页面可见性矩阵">
          <VCardText>
            <VAlert
              v-if="selected === 'admin'"
              type="info"
              variant="tonal"
              class="mb-4"
            >
              管理员始终保留系统设置入口，避免把自己锁在权限页外。
            </VAlert><div
              v-for="group in menuGroups"
              :key="group.id"
              class="mb-5"
            >
              <div class="d-flex align-center justify-space-between mb-2">
                <div class="font-weight-medium">
                  {{ t(`menu.${group.id}`) }}
                </div><VSwitch
                  v-model="hiddenGroups"
                  :value="group.id"
                  label="隐藏分组"
                  density="compact"
                  hide-details
                  :disabled="selected === 'admin' || group.id === 'admin'"
                />
              </div><VRow>
                <VCol
                  v-for="page in pageCatalog.filter(item => item.group === group.id && item.showInMenu)"
                  :key="page.id"
                  cols="12"
                  sm="6"
                >
                  <VCheckbox
                    :model-value="!hiddenPageIds.includes(page.id)"
                    :label="page.name['zh-CN']"
                    :disabled="selected === 'admin' || group.id === 'admin'"
                    @update:model-value="togglePage(page.id)"
                  />
                </VCol>
              </VRow>
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
    <FormDrawer
      v-model="copyDrawer"
      title="复制并保存角色（模拟）"
      @save="saveCopy"
    >
      <VAlert
        type="info"
        variant="tonal"
        class="mb-4"
      >
        从「店铺运营」复制，保存父角色继承、数据范围、用户指派和审计记录。
      </VAlert>
      <AppTextField
        v-model="copyName"
        label="新角色中文名"
        class="mb-4"
        :rules="[requiredValidator]"
      />
      <AppTextField
        v-model="copyNameEn"
        label="新角色英文名"
        class="mb-4"
      />
      <AppSelect
        v-model="copyScope"
        label="数据范围"
        :items="[{ title: '欧洲店铺', value: 'store' }, { title: '本部门', value: 'department' }, { title: '本人', value: 'self' }, { title: '全部', value: 'all' }]"
        class="mb-4"
      />
      <AppTextField
        v-model="copyUsers"
        label="指派用户（逗号分隔）"
      />
    </FormDrawer>
  </div>
</template>
