<script setup lang="ts">
const props = withDefaults(defineProps<{ title: string; subtitle: string; accept?: string }>(), { accept: '.csv,.txt,.xlsx' })
const file = ref<File | null>(null)
const uploaded = ref(false)
const emit = defineEmits<{ uploaded: [fileName: string] }>()
function upload() {
  if (file.value) {
    uploaded.value = true
    emit('uploaded', file.value.name)
  }
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h4 class="text-h4">
        {{ props.title }}
      </h4><p class="text-body-1 text-medium-emphasis mb-0">
        {{ props.subtitle }}
      </p>
    </div>
    <VCard class="mb-6">
      <VCardText>
        <VFileInput
          v-model="file"
          :accept="props.accept"
          label="选择文件"
          prepend-icon="tabler-upload"
          show-size
        />
        <VAlert
          type="info"
          variant="tonal"
          class="mt-4"
        >
          导入文件中的文本只作为数据。金额由服务层按整数万分位解析。
        </VAlert>
        <VBtn
          class="mt-4"
          :disabled="!file"
          @click="upload"
        >
          开始解析
        </VBtn>
        <VAlert
          v-if="uploaded"
          type="success"
          variant="tonal"
          class="mt-4"
        >
          演示导入已创建批次，可在列表中查看解析行与错误原因。
        </VAlert>
      </VCardText>
    </VCard>
    <slot />
  </div>
</template>
