import React, { useMemo, useState } from "react";
import { RevenueSummary } from "./RevenueSummary";

const PROPERTIES = [
  { id: 'prop-001', name: 'Beach House Alpha' },
  { id: 'prop-002', name: 'City Apartment Downtown' },
  { id: 'prop-003', name: 'Country Villa Estate' },
  { id: 'prop-004', name: 'Lakeside Cottage' },
  { id: 'prop-005', name: 'Urban Loft Modern' }
];

const Dashboard: React.FC = () => {
  const [selectedProperty, setSelectedProperty] = useState('prop-001');
  // Sample seed data is March 2024; default matches board "March" narrative in ASSIGNMENT.md
  const [periodYm, setPeriodYm] = useState('2024-03');
  const { y, m } = useMemo(() => {
    const match = /^(\d{4})-(\d{2})$/.exec(periodYm);
    if (!match) return { y: 2024, m: 3 };
    return { y: parseInt(match[1], 10), m: parseInt(match[2], 10) };
  }, [periodYm]);

  return (
    <div className="p-4 lg:p-6 min-h-full">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-900">Property Management Dashboard</h1>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 lg:p-6">
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
              <div>
                <h2 className="text-lg lg:text-xl font-medium text-gray-900 mb-2">Revenue Overview</h2>
                <p className="text-sm lg:text-base text-gray-600">
                  Revenue for the selected calendar month uses check-in dates in each property&apos;s
                  local timezone, so March matches finance month roll-ups.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
                <div className="flex flex-col sm:items-end">
                  <label className="text-xs font-medium text-gray-700 mb-1" htmlFor="revenue-period">
                    Month
                  </label>
                  <input
                    id="revenue-period"
                    type="month"
                    className="block w-full sm:w-auto min-w-[200px] px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                    value={periodYm}
                    onChange={(e) => setPeriodYm(e.target.value)}
                  />
                </div>
                <div className="flex flex-col sm:items-end">
                  <label className="text-xs font-medium text-gray-700 mb-1" htmlFor="revenue-property">
                    Select Property
                  </label>
                  <select
                    id="revenue-property"
                    value={selectedProperty}
                    onChange={(e) => setSelectedProperty(e.target.value)}
                    className="block w-full sm:w-auto min-w-[200px] px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  >
                    {PROPERTIES.map((property) => (
                      <option key={property.id} value={property.id}>
                        {property.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <RevenueSummary propertyId={selectedProperty} year={y} month={m} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
