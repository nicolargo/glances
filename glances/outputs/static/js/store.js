import { reactive } from 'vue';

export const store = reactive({
    args: undefined,
    config: undefined,
    data: undefined,
    status: 'IDLE'
});
