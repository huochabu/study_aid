<!-- frontend/src/components/EvidencePanel.vue -->
<template>
  <div class="evidence-panel">
    <div v-if="!kg" class="placeholder">暂无知识图谱</div>
    <div v-else>
      <div class="nodes">
        <h4>节点</h4>
        <ul>
          <li v-for="node in kg.nodes" :key="node.id">
            <strong>{{ node.label }}</strong> ({{ node.type }})
          </li>
        </ul>
      </div>
      <div class="edges">
        <h4>关系</h4>
        <ul>
          <li v-for="edge in kg.edges" :key="edge.source + '-' + edge.target">
            {{ edge.source }} → {{ edge.target }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  kg: {
    type: Object,
    default: null
  }
})
</script>

<style scoped>
.evidence-panel {
  font-family: Arial, sans-serif;
}
.nodes, .edges {
  margin: 10px 0;
}
ul {
  list-style-type: none;
  padding-left: 20px;
}
li {
  margin: 5px 0;
  color: #333;
}
</style>