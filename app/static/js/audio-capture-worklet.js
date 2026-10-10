class CompanionCapture extends AudioWorkletProcessor {
    constructor() {
        super();
        this.pending = new Float32Array(1024);
        this.offset = 0;
    }
    process(inputs, outputs) {
        const channels = inputs[0];
        if (channels && channels.length && channels[0].length) {
            for (let i = 0; i < channels[0].length; i++) {
                let value = 0;
                for (const channel of channels) value += channel[i] / channels.length;
                this.pending[this.offset++] = value;
                if (this.offset === this.pending.length) {
                    this.port.postMessage(this.pending, [this.pending.buffer]);
                    this.pending = new Float32Array(1024);
                    this.offset = 0;
                }
            }
        }
        for (const output of outputs) for (const channel of output) channel.fill(0);
        return true;
    }
}
registerProcessor('companion-capture', CompanionCapture);
