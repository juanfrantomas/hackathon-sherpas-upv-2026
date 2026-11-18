import Fastify from 'fastify';
import multipart from '@fastify/multipart';
import { config, validateLiveConfig } from './config.js';
import { registerRoutes } from './api/routes.js';

validateLiveConfig();
const app = Fastify({
  logger: {
    redact: ['req.headers.authorization', 'req.headers.x-llm-api-key'],
  },
  bodyLimit: 7 * 1024 * 1024,
});

await app.register(multipart, {
  limits: { files: 3, fields: 0, fileSize: 2 * 1024 * 1024 },
  throwFileSizeLimit: true,
});
await registerRoutes(app);

try {
  await app.listen({ host: config.HOST, port: config.PORT });
} catch (error) {
  app.log.error(error);
  process.exit(1);
}
