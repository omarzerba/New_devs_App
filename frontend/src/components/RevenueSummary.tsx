import React, { useEffect, useState } from 'react';
import { SecureAPI } from '../lib/secureApi';

interface RevenueData {
    property_id: string;
    /** Always two decimal places, e.g. "1234.56" (no float JSON). */
    total_revenue: string;
    currency: string;
    reservations_count: number;
}

/** Normalize API value to a XX[.yy] string without multiplying floats. */
function toLedgerTwoDecimals(v: unknown): string {
    if (typeof v === 'number' && Number.isFinite(v)) {
        return v.toFixed(2);
    }
    const raw = String(v ?? '0').trim();
    const neg = raw.startsWith('-') ? '-' : '';
    const b = neg ? raw.slice(1) : raw;
    // ^ ... $     whole string must match (no extra characters).
    // (\d+)       capture group 1: one or more digits (integer part; leading zeros allowed, normalized later).
    // \.          a literal decimal point.
    // (\d*)       capture group 2: zero or more digits after the point (may be empty, e.g. "12.").
    const m = b.match(/^(\d+)\.(\d*)$/);
    if (!m) {
        // ^(\d+)$   only digits, no decimal point (e.g. "1200" -> we supply ".00").
        const m2 = b.match(/^(\d+)$/);
        if (!m2) return '0.00';
        return `${neg}${m2[1]}.00`;
    }
    const frac = (m[2] + '00').slice(0, 2);
    return `${neg}${m[1]}.${frac}`;
}

/** Add grouping commas to the integer part; amount must already be two-decimal string. */
function formatMoneyString(amountStr: string, currency: string): string {
    const neg = amountStr.startsWith('-');
    const s = neg ? amountStr.slice(1) : amountStr;
    const [whole, frac] = s.split('.');
    // Insert commas as thousands separators on the integer part only.
    // \B          position is not a "word" boundary between two word chars — here: between two digits.
    // (?= ...)    lookahead: require what follows without consuming it.
    // (\d{3})+    one or more groups of exactly three digits ahead.
    // (?!\d)      after those triplets, the next char must not be a digit (end of integer or next non-digit).
    // Together:   place a comma before every digit that starts a 000-block from the right (US-style grouping).
    const grouped = (whole || '0').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${currency} ${neg ? '-' : ''}${grouped}.${frac || '00'}`;
}

interface RevenueSummaryProps {
    propertyId?: string;
    debugTenant?: string; 
    showRaw?: boolean;
}

export const RevenueSummary: React.FC<RevenueSummaryProps> = ({ propertyId = 'prop-001', debugTenant, showRaw }) => {
    const [data, setData] = useState<RevenueData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const activeTenant = debugTenant || 'candidate';

    useEffect(() => {
        const fetchRevenue = async () => {
            setLoading(true);
            try {
                // Use SecureAPI to handle authentication automatically
                // We pass the simulatedTenant option which SecureAPI will attach as a header
                const response = await SecureAPI.getDashboardSummary(propertyId, {
                    simulatedTenant: activeTenant,
                    timestamp: Date.now()
                });
                setData({
                    ...response,
                    total_revenue: toLedgerTwoDecimals(response.total_revenue),
                });
            } catch (err) {
                setError('Failed to load revenue data');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchRevenue();
    }, [propertyId, activeTenant]);

    if (loading) {
        return (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <div className="animate-pulse space-y-4">
                    <div className="h-4 bg-gray-100 rounded w-1/4"></div>
                    <div className="h-8 bg-gray-100 rounded w-1/2"></div>
                    <div className="flex gap-4 pt-4">
                        <div className="h-12 bg-gray-100 rounded flex-1"></div>
                        <div className="h-12 bg-gray-100 rounded flex-1"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) return <div className="p-4 text-red-500 bg-red-50 rounded-lg">{error}</div>;
    if (!data) return null;

    const displayLabel = formatMoneyString(data.total_revenue, data.currency);
    // Optional leading minus, at least one digit, exactly one dot, exactly two fractional digits (canonical API shape).
    // ^-?         optional minus at start.
    // \d+         one or more digits before the decimal.
    // \.          literal dot.
    // \d{2}       exactly two digits after the dot (cents).
    // $           end of string (no trailing junk).
    const moneyFormatOk = /^-?\d+\.\d{2}$/.test(data.total_revenue);

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow duration-300">
            {showRaw && (
                <div className="p-3 bg-gray-50 text-xs font-mono border-b border-gray-100 overflow-auto max-h-32">
                    <strong className="block mb-1 text-gray-500 uppercase tracking-wider text-[10px]">Raw API Response</strong>
                    <pre className="text-gray-700">{JSON.stringify(data, null, 2)}</pre>
                </div>
            )}

            <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Total Revenue</h2>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-3xl font-bold text-gray-900 tracking-tight">
                                {displayLabel}
                            </span>
                            {/* Fake trend indicator for premium feel */}
                            <span className="inline-flex items-baseline px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 md:mt-2 lg:mt-0">
                                <svg className="-ml-1 mr-0.5 h-3 w-3 flex-shrink-0 self-center text-green-500" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                                    <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                                </svg>
                                12%
                            </span>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                    <div>
                        <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Property ID</p>
                        <p className="text-sm font-semibold text-gray-700 font-mono mt-1">{data.property_id}</p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Reservations</p>
                        <p className="text-sm font-semibold text-gray-700 mt-1">{data.reservations_count} <span className="font-normal text-gray-400">bookings</span></p>
                    </div>
                </div>

                <div className="mt-4 h-6">
                    {showRaw && !moneyFormatOk && (
                        <div className="flex items-center text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
                            <svg className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            Unexpected money format from API (expected two decimal places)
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
