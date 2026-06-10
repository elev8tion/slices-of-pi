<script setup lang="ts">
</script>

<template>
  <div class="flex flex-wrap gap-1.5">
    <span class="tag production">● production <span class="count">0</span></span>
    <span class="tag staging">● staging <span class="count">0</span></span>
    <span class="tag dev">● dev <span class="count">0</span></span>
    <span class="tag">code-review <span class="count">0</span></span>
    <span class="tag">monitoring <span class="count">0</span></span>
  </div>
</template>

<style scoped>
.tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px 3px 8px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.4);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.32,0.72,0,1);
}
.tag:hover {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.6);
}
.tag .count {
  background: rgba(255,255,255,0.06);
  padding: 0 5px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  color: rgba(255,255,255,0.3);
}
.tag.production { border-color: rgba(34,197,94,0.15); color: rgba(34,197,94,0.7); }
.tag.staging { border-color: rgba(234,179,8,0.15); color: rgba(234,179,8,0.7); }
.tag.dev { border-color: rgba(99,102,241,0.15); color: rgba(99,102,241,0.6); }
</style>
