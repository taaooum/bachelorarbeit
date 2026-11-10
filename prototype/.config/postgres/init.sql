SELECT 'CREATE DATABASE default'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'default')\gexec

SELECT 'CREATE DATABASE litellm'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'litellm')\gexec
