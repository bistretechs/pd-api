import os

file_path = "web/features/production-analytics/components/ProductionAnalyticsWorkspace.tsx"

with open(file_path, "r") as f:
    orig = f.read()

new_content = """"use client";

import type { ReactElement } from "react";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
    AlertCircleIcon,
    BarChart3Icon,
    CheckCircle2Icon,
    Clock3Icon,
    RefreshCcwIcon,
    ShieldCheckIcon,
    Users2Icon,
    ArrowRightIcon,
    ActivityIcon,
} from "lucide-react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import {
    fetchProductionAnalyticsData,
    fetchRecentProductionJobs,
} from "@/lib/api/production-analytics";
import type { Job } from "@/types/jobs";
import type {
    JobStatusDistributionItem,
    ProductionAnalyticsData,
    TeamPerformanceItem,
} from "@/types/production-analytics";

interface StatusChartItem {
    name: string;
    value: number;
    color: string;
}

const STATUS_COLORS: string[] = [
    "#093756", // brand-blue
    "#F6B619", // brand-yellow
    "#009444", // brand-green
    "#F15A29", // brand-orange
    "#662D91", // brand-purple
    "#ED1C24", // brand-red
];

const toTitleCase = (value: string): string => {
    return value
        .replaceAll("_", " ")
        .split(" ")
        .filter((part: string): boolean => part.length > 0)
        .map((part: string): string => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
};

const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`;
};

const formatCurrency = (value: number | null): string => {
    if (value === null) {
        return "—";
    }

    return `KES ${value.toLocaleString()}`;
};

const formatDate = (value: string | null): string => {
    if (!value) {
        return "Not set";
    }

    const dateValue = new Date(value);
    if (Number.isNaN(dateValue.getTime())) {
        return "Not set";
    }

    return dateValue.toLocaleDateString("en-KE", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
};

const getStatusBadgeClass = (status: string): string => {
    if (status === "completed") {
        return "bg-brand-green/10 text-brand-green border-brand-green/20";
    }

    if (status === "in_progress") {
        return "bg-brand-blue/10 text-brand-blue border-brand-blue/20";
    }

    if (status === "on_hold") {
        return "bg-brand-orange/10 text-brand-orange border-brand-orange/20";
    }

    return "bg-brand-yellow/10 text-brand-yellow border-brand-yellow/20";
};

const buildStatusChartData = (items: JobStatusDistributionItem[]): StatusChartItem[] => {
    return items.map((item: JobStatusDistributionItem, index: number): StatusChartItem => {
        return {
            name: toTitleCase(item.status),
            value: item.count,
            color: STATUS_COLORS[index % STATUS_COLORS.length],
        };
    });
};

const getAverageCompletionRate = (items: TeamPerformanceItem[]): number => {
    if (items.length === 0) {
        return 0;
    }

    const totalCompletionRate = items.reduce((sum: number, item: TeamPerformanceItem): number => {
        return sum + item.completion_rate;
    }, 0);

    return totalCompletionRate / items.length;
};

// Custom Tooltip for Bar Chart
const BarChartTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white p-3 border border-gray-200 shadow-xl rounded-xl">
                <p className="font-semibold text-gray-900 mb-1">{label}</p>
                <div className="flex items-center gap-2">
                    <div className="h-2.5 w-2.5 rounded-full bg-brand-blue"></div>
                    <p className="text-gray-700 font-medium">
                        {payload[0].value.toFixed(1)}% <span className="text-gray-500 font-normal text-xs ml-1">Completion</span>
                    </p>
                </div>
            </div>
        );
    }
    return null;
};

// Custom Tooltip for Pie Chart
const PieChartTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white p-3 border border-gray-200 shadow-xl rounded-xl">
                <div className="flex items-center gap-2 mb-1">
                    <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: payload[0].payload.fill }}></div>
                    <p className="font-semibold text-gray-900">{payload[0].name}</p>
                </div>
                <p className="text-gray-700 font-medium">
                    {payload[0].value.toLocaleString()} <span className="text-gray-500 font-normal text-xs ml-1">Jobs</span>
                </p>
            </div>
        );
    }
    return null;
};

export default function ProductionAnalyticsWorkspace(): ReactElement {
    const analyticsQuery = useQuery({
        queryKey: ["production-analytics"],
        queryFn: fetchProductionAnalyticsData,
    });

    const recentJobsQuery = useQuery({
        queryKey: ["production-analytics-jobs"],
        queryFn: (): Promise<Job[]> => fetchRecentProductionJobs(6),
    });

    const analytics: ProductionAnalyticsData | undefined = analyticsQuery.data;
    const statusChartData = useMemo((): StatusChartItem[] => {
        return buildStatusChartData(analytics?.job_status_distribution ?? []);
    }, [analytics?.job_status_distribution]);

    const averageTeamCompletion = useMemo((): number => {
        return getAverageCompletionRate(analytics?.team_performance ?? []);
    }, [analytics?.team_performance]);

    const totalTrackedJobs = useMemo((): number => {
        return (analytics?.job_status_distribution ?? []).reduce((sum: number, item: JobStatusDistributionItem): number => {
            return sum + item.count;
        }, 0);
    }, [analytics?.job_status_distribution]);

    if (analyticsQuery.isLoading) {
        return (
            <main className="bg-[#f8fafc] min-h-screen pb-12">
                <header className="bg-white border-b border-gray-200 px-8 py-6">
                    <div className="h-4 w-48 animate-pulse rounded bg-gray-200" />
                    <div className="mt-4 h-8 w-72 animate-pulse rounded bg-gray-200" />
                </header>
                <div className="max-w-7xl mx-auto px-8 py-8 space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {Array.from({ length: 4 }).map((_, i) => (
                            <div key={i} className="h-32 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
                                <div className="h-4 w-32 animate-pulse rounded bg-gray-200 mb-4" />
                                <div className="h-8 w-24 animate-pulse rounded bg-gray-200" />
                            </div>
                        ))}
                    </div>
                </div>
            </main>
        );
    }

    if (analyticsQuery.isError || !analytics) {
        return (
            <main className="bg-[#f8fafc] min-h-screen pb-12">
                <header className="bg-white border-b border-gray-200 px-8 py-6">
                    <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Production Analytics</h1>
                </header>
                <div className="max-w-4xl mx-auto px-8 py-12">
                    <div className="rounded-2xl border border-brand-red/20 bg-brand-red/5 p-8 text-center">
                        <AlertCircleIcon className="h-12 w-12 text-brand-red mx-auto mb-4" />
                        <h2 className="text-lg font-semibold text-brand-red">Unable to load production analytics</h2>
                        <p className="mt-2 text-gray-600">The analytics service did not return data. Please try again later.</p>
                        <button
                            type="button"
                            onClick={() => {
                                void analyticsQuery.refetch();
                                void recentJobsQuery.refetch();
                            }}
                            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 shadow-sm"
                        >
                            <RefreshCcwIcon className="h-4 w-4" />
                            Retry
                        </button>
                    </div>
                </div>
            </main>
        );
    }

    return (
        <main className="bg-[#f8fafc] min-h-screen pb-12">
            <header className="bg-white border-b border-gray-200">
                <div className="max-w-7xl mx-auto px-8 py-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                        <nav className="flex items-center gap-2 text-xs font-medium text-gray-500 mb-3">
                            <Link href="/production-team" className="hover:text-brand-blue transition-colors">Production Team</Link>
                            <span>/</span>
                            <span className="text-gray-900">Analytics</span>
                        </nav>
                        <h1 className="text-3xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
                            Production Analytics
                            <span className="inline-flex items-center gap-1.5 rounded-md bg-brand-blue/10 px-2.5 py-1 text-xs font-semibold text-brand-blue">
                                <ActivityIcon className="h-3.5 w-3.5" />
                                Live View
                            </span>
                        </h1>
                        <p className="mt-2 text-sm text-gray-500">
                            Operations-focused visibility for turnaround, quality, and team execution.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() => {
                            void analyticsQuery.refetch();
                            void recentJobsQuery.refetch();
                        }}
                        className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition-all hover:border-brand-blue hover:text-brand-blue focus:ring-2 focus:ring-brand-blue/20"
                    >
                        <RefreshCcwIcon className={`h-4 w-4 ${analyticsQuery.isFetching ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-8 py-8 space-y-8">
                {/* Metrics Row */}
                <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <article className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)] transition-all hover:shadow-md hover:border-brand-blue/30">
                        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-brand-blue/5 blur-2xl transition-all group-hover:bg-brand-blue/10" />
                        <div className="relative z-10">
                            <div className="flex items-center justify-between">
                                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Avg Turnaround</p>
                                <div className="rounded-lg bg-brand-blue/10 p-2 text-brand-blue">
                                    <Clock3Icon className="h-4 w-4" />
                                </div>
                            </div>
                            <div className="mt-4 flex items-baseline gap-1">
                                <h3 className="text-3xl font-bold tracking-tight text-gray-900">{analytics.average_turnaround_days.toFixed(1)}</h3>
                                <span className="text-sm font-medium text-gray-500">days</span>
                            </div>
                        </div>
                    </article>

                    <article className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)] transition-all hover:shadow-md hover:border-brand-red/30">
                        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-brand-red/5 blur-2xl transition-all group-hover:bg-brand-red/10" />
                        <div className="relative z-10">
                            <div className="flex items-center justify-between">
                                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">QC Rejection</p>
                                <div className="rounded-lg bg-brand-red/10 p-2 text-brand-red">
                                    <ShieldCheckIcon className="h-4 w-4" />
                                </div>
                            </div>
                            <h3 className="mt-4 text-3xl font-bold tracking-tight text-gray-900">{formatPercentage(analytics.qc_rejection_rate)}</h3>
                        </div>
                    </article>

                    <article className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)] transition-all hover:shadow-md hover:border-brand-green/30">
                        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-brand-green/5 blur-2xl transition-all group-hover:bg-brand-green/10" />
                        <div className="relative z-10">
                            <div className="flex items-center justify-between">
                                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Vendor On-Time</p>
                                <div className="rounded-lg bg-brand-green/10 p-2 text-brand-green">
                                    <CheckCircle2Icon className="h-4 w-4" />
                                </div>
                            </div>
                            <h3 className="mt-4 text-3xl font-bold tracking-tight text-gray-900">{formatPercentage(analytics.vendor_on_time_rate)}</h3>
                        </div>
                    </article>

                    <article className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)] transition-all hover:shadow-md hover:border-brand-purple/30">
                        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-brand-purple/5 blur-2xl transition-all group-hover:bg-brand-purple/10" />
                        <div className="relative z-10">
                            <div className="flex items-center justify-between">
                                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Monthly Rev</p>
                                <div className="rounded-lg bg-brand-purple/10 p-2 text-brand-purple">
                                    <BarChart3Icon className="h-4 w-4" />
                                </div>
                            </div>
                            <h3 className="mt-4 text-2xl font-bold tracking-tight text-gray-900 truncate" title={formatCurrency(analytics.monthly_revenue)}>
                                {formatCurrency(analytics.monthly_revenue)}
                            </h3>
                        </div>
                    </article>
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Charts Section */}
                    <div className="lg:col-span-2 space-y-8">
                        <article className="rounded-2xl border border-gray-200 bg-white p-6 sm:p-8 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)]">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                                <div>
                                    <h2 className="text-lg font-bold text-gray-900">Completion Performance</h2>
                                    <p className="text-sm text-gray-500 mt-1">Completion rates across the production team</p>
                                </div>
                                <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-brand-blue/5 border border-brand-blue/10 px-3 py-1.5 text-xs font-semibold text-brand-blue">
                                    <Users2Icon className="h-3.5 w-3.5" />
                                    {analytics.team_performance.length} Members tracked
                                </span>
                            </div>

                            {analytics.team_performance.length === 0 ? (
                                <div className="h-[300px] rounded-xl border border-dashed border-gray-300 bg-gray-50 flex items-center justify-center text-sm text-gray-500">
                                    Team performance data is not available yet.
                                </div>
                            ) : (
                                <div className="h-[300px]">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={analytics.team_performance} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                                            <XAxis 
                                                dataKey="user_name" 
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{ fill: "#6B7280", fontSize: 13, fontWeight: 500 }} 
                                                dy={10}
                                            />
                                            <YAxis
                                                domain={[0, 100]}
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{ fill: "#6B7280", fontSize: 12 }}
                                                tickFormatter={(value: number): string => `${value}%`}
                                            />
                                            <Tooltip content={<BarChartTooltip />} cursor={{ fill: "#F3F4F6", opacity: 0.4 }} />
                                            <Bar dataKey="completion_rate" fill="#093756" radius={[4, 4, 0, 0]} maxBarSize={48} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            )}
                        </article>

                        <article className="rounded-2xl border border-gray-200 bg-white shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)] overflow-hidden">
                            <div className="p-6 sm:p-8 border-b border-gray-100 flex items-center justify-between">
                                <div>
                                    <h2 className="text-lg font-bold text-gray-900">Recent Jobs</h2>
                                    <p className="text-sm text-gray-500 mt-1">Latest production jobs updated recently</p>
                                </div>
                                <Link 
                                    href="/production-team/my-jobs" 
                                    className="group inline-flex items-center gap-1 text-sm font-semibold text-brand-blue transition-colors hover:text-brand-blue/80"
                                >
                                    View all
                                    <ArrowRightIcon className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                                </Link>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="bg-gray-50/50">
                                            <th className="whitespace-nowrap px-6 py-4 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-100">Job</th>
                                            <th className="whitespace-nowrap px-6 py-4 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-100">Client</th>
                                            <th className="whitespace-nowrap px-6 py-4 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-100">Product</th>
                                            <th className="whitespace-nowrap px-6 py-4 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-100">Due</th>
                                            <th className="whitespace-nowrap px-6 py-4 text-xs font-semibold uppercase tracking-wider text-gray-500 border-b border-gray-100 text-right">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100">
                                        {recentJobsQuery.isLoading ? (
                                            <tr>
                                                <td colSpan={5} className="p-6 border-b-0">
                                                    <div className="space-y-4">
                                                        {Array.from({ length: 4 }).map((_, i) => (
                                                            <div key={i} className="h-10 animate-pulse rounded-lg bg-gray-100" />
                                                        ))}
                                                    </div>
                                                </td>
                                            </tr>
                                        ) : recentJobsQuery.isError ? (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-10 text-center text-sm text-brand-red/80">
                                                    Unable to load recent jobs.
                                                </td>
                                            </tr>
                                        ) : (recentJobsQuery.data ?? []).length === 0 ? (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-10 text-center text-sm text-gray-500">
                                                    No recent production jobs found.
                                                </td>
                                            </tr>
                                        ) : (
                                            (recentJobsQuery.data ?? []).map((job: Job): ReactElement => (
                                                <tr key={job.id} className="transition-colors hover:bg-gray-50/50">
                                                    <td className="whitespace-nowrap px-6 py-4 text-sm font-semibold text-gray-900">
                                                        <Link href={`/production-team/my-jobs/${job.id}`} className="hover:text-brand-blue hover:underline">
                                                            {job.job_number || `#${job.id}`}
                                                        </Link>
                                                    </td>
                                                    <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-700">
                                                        {job.client?.name || <span className="text-gray-400 italic">Unassigned</span>}
                                                    </td>
                                                    <td className="px-6 py-4 text-sm text-gray-600 max-w-[200px] truncate" title={job.product ?? ""}>
                                                        {job.product || <span className="text-gray-400 italic">Not set</span>}
                                                    </td>
                                                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">{formatDate(job.expected_completion)}</td>
                                                    <td className="whitespace-nowrap px-6 py-4 text-right">
                                                        <span className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-semibold ${getStatusBadgeClass(job.status)}`}>
                                                            {toTitleCase(job.status)}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </article>
                    </div>

                    {/* Sidebar Section */}
                    <div className="space-y-8">
                        <article className="rounded-2xl border border-gray-200 bg-white p-6 sm:p-8 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)]">
                            <h2 className="text-lg font-bold text-gray-900 mb-1">Job Status Map</h2>
                            <p className="text-sm text-gray-500 mb-6">{totalTrackedJobs.toLocaleString()} jobs currently tracked</p>

                            {statusChartData.length === 0 ? (
                                <div className="h-[240px] rounded-xl border border-dashed border-gray-300 bg-gray-50 flex items-center justify-center text-sm text-gray-500">
                                    Status data is not available yet.
                                </div>
                            ) : (
                                <div className="h-[260px] relative">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={statusChartData}
                                                dataKey="value"
                                                nameKey="name"
                                                innerRadius={68}
                                                outerRadius={96}
                                                paddingAngle={3}
                                                stroke="none"
                                            >
                                                {statusChartData.map((item: StatusChartItem): ReactElement => (
                                                    <Cell key={item.name} fill={item.color} />
                                                ))}
                                            </Pie>
                                            <Tooltip content={<PieChartTooltip />} />
                                            <Legend 
                                                verticalAlign="bottom" 
                                                height={40} 
                                                iconType="circle" 
                                                iconSize={8}
                                                wrapperStyle={{ fontSize: '13px', color: '#4B5563', paddingTop: '20px' }}
                                            />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                            )}
                        </article>

                        <article className="rounded-2xl border border-gray-200 bg-Brand-blue/5 p-6 sm:p-8 bg-gradient-to-b from-white to-gray-50/80 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)]">
                            <h2 className="text-lg font-bold text-gray-900 mb-6">Quick Summary</h2>

                            <div className="space-y-4">
                                <div className="group rounded-xl border border-gray-100 bg-white hover:border-brand-blue/30 transition-colors p-4 shadow-sm">
                                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Team Average</p>
                                    <div className="flex items-end gap-2">
                                        <span className="text-2xl font-bold text-brand-blue">{formatPercentage(averageTeamCompletion)}</span>
                                        <span className="text-sm font-medium text-gray-500 mb-1">completion</span>
                                    </div>
                                </div>

                                <div className="group rounded-xl border border-gray-100 bg-white hover:border-gray-300 transition-colors p-4 shadow-sm">
                                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Total Pipeline</p>
                                    <div className="flex items-end gap-2">
                                        <span className="text-2xl font-bold text-gray-900">{totalTrackedJobs.toLocaleString()}</span>
                                        <span className="text-sm font-medium text-gray-500 mb-1">active records</span>
                                    </div>
                                </div>

                                <div className="group rounded-xl border border-gray-100 bg-white hover:border-brand-yellow/50 transition-colors p-4 shadow-sm">
                                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Top Performer</p>
                                    <div className="flex items-center gap-3 mt-1">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-yellow/20 text-brand-yellow font-bold text-lg">
                                            {analytics.team_performance.length > 0
                                                ? analytics.team_performance
                                                    .slice()
                                                    .sort((first, second) => second.completion_rate - first.completion_rate)[0].user_name.charAt(0).toUpperCase()
                                                : "?"}
                                        </div>
                                        <div className="flex-1 overflow-hidden">
                                            <p className="text-base font-bold text-gray-900 truncate">
                                                {analytics.team_performance.length > 0
                                                    ? analytics.team_performance
                                                        .slice()
                                                        .sort((first, second) => second.completion_rate - first.completion_rate)[0].user_name
                                                    : "Not available"}
                                            </p>
                                            {analytics.team_performance.length > 0 && (
                                                <p className="text-xs text-gray-500 font-medium">Leading completion rate</p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </article>
                    </div>
                </div>
            </div>
        </main>
    );
}
"""

with open(file_path, "w") as f:
    f.write(new_content)

print("Rewritten successfully")
