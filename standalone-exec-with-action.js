// Standalone Express server to validate /exec-with-action endpoint logic from VSCode extension

const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.text({ limit: '50mb' }));

// /exec-with-action endpoint logic copied from extension
app.post('/exec-with-action', async (req, res) => {
    try {
        const code = typeof req.body === 'string' ? req.body : req.body.code;
        const onResult = req.body.onResult;
        // Create a safe execution context (no vscode API here)
        const context = {
            console,
            setTimeout,
            setInterval,
            clearTimeout,
            clearInterval,
            Promise
        };
        const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
        const func = new AsyncFunction('console', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'Promise', code);
        const result = await func(
            context.console,
            context.setTimeout,
            context.setInterval,
            context.clearTimeout,
            context.clearInterval,
            context.Promise
        );
        let actionResult = null;
        if (onResult) {
            // onResult is a JS function body as string, receives 'result' as argument
            const actionFunc = new AsyncFunction('result', 'console', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'Promise', onResult);
            actionResult = await actionFunc(
                result,
                context.console,
                context.setTimeout,
                context.setInterval,
                context.clearTimeout,
                context.clearInterval,
                context.Promise
            );
        }
        res.json({ success: true, result, actionResult });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
    console.log(`Standalone Express server running on http://localhost:${PORT}`);
});
