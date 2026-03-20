/**
 * Centralized Logging Utility
 * Provides consistent logging across the entire app
 * with different log levels and optional persistence
 */

export enum LogLevel {
    INFO = 'INFO',
    DEBUG = 'DEBUG',
    WARN = 'WARN',
    ERROR = 'ERROR',
}

interface LogEntry {
    timestamp: string;
    level: LogLevel;
    message: string;
    data?: any;
}

class Logger {
    private logs: LogEntry[] = [];
    private maxLogs = 500; // Keep last 500 log entries
    private isDevelopment = __DEV__;

    private formatTimestamp(): string {
        return new Date().toISOString();
    }

    private addLog(level: LogLevel, message: string, data?: any): void {
        const entry: LogEntry = {
            timestamp: this.formatTimestamp(),
            level,
            message,
            data,
        };

        this.logs.push(entry);

        // Keep only the last N logs
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(-this.maxLogs);
        }

        // Print to console in development
        if (this.isDevelopment) {
            const prefix = `[${level}] ${entry.timestamp}`;
            if (data !== undefined) {
                console.log(prefix, message, data);
            } else {
                console.log(prefix, message);
            }
        }
    }

    info(message: string, data?: any): void {
        this.addLog(LogLevel.INFO, message, data);
    }

    debug(message: string, data?: any): void {
        this.addLog(LogLevel.DEBUG, message, data);
    }

    warn(message: string, data?: any): void {
        this.addLog(LogLevel.WARN, message, data);
        if (this.isDevelopment) {
            console.warn(`[WARN] ${message}`, data);
        }
    }

    error(message: string, error?: any): void {
        const errorData = error instanceof Error 
            ? { 
                message: error.message, 
                stack: error.stack 
              } 
            : error;
        this.addLog(LogLevel.ERROR, message, errorData);
        if (this.isDevelopment) {
            console.error(`[ERROR] ${message}`, errorData);
        }
    }

    /**
     * Get all logs as a string for debugging
     */
    getLogsDump(): string {
        return this.logs
            .map(
                (log) =>
                    `[${log.timestamp}] ${log.level}: ${log.message}${
                        log.data ? ' ' + JSON.stringify(log.data) : ''
                    }`
            )
            .join('\n');
    }

    /**
     * Get logs filtered by level
     */
    getLogsByLevel(level: LogLevel): LogEntry[] {
        return this.logs.filter((log) => log.level === level);
    }

    /**
     * Clear all logs
     */
    clearLogs(): void {
        this.logs = [];
    }

    /**
     * Get recent logs
     */
    getRecentLogs(count: number = 50): LogEntry[] {
        return this.logs.slice(-count);
    }
}

export default new Logger();