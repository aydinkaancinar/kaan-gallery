"use client";

import { useState } from "react";

type MonthRangeProps = {
  earliest?: string | null;
  latest?: string | null;
  createdFrom?: string;
  createdTo?: string;
  onCommit?: (from: string, to: string) => void;
};

function apiMonth(index: number) {
  const year = Math.floor(index / 12);
  const month = index % 12 + 1;

  return `${year}-${String(month).padStart(2, "0")}`;
}

function monthIndex(value: string) {
  const [year, month] = value.split("-").map(Number);
  return year * 12 + month - 1;
}

function monthLabel(index: number) {
  const year = Math.floor(index / 12);
  const month = index % 12 + 1;

  return `${String(month).padStart(2, "0")}/${String(year).slice(-2)}`;
}

function accessibleMonth(index: number) {
  return new Intl.DateTimeFormat("en", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(
    new Date(Date.UTC(Math.floor(index / 12), index % 12, 1))
  );
}

function position(index: number, lastMonth: number) {
  const ratio = lastMonth === 0 ? 0.5 : index / lastMonth;
  return `calc(${ratio * 100}% + ${12 - 24 * ratio}px)`;
}

export default function MonthRange({
  earliest,
  latest,
  createdFrom,
  createdTo,
  onCommit,
}: MonthRangeProps) {
  const baseMonth = earliest ? monthIndex(earliest) : 0;
  const lastMonth =
    earliest && latest ? monthIndex(latest) - baseMonth : 0;

  function selectedOffset(value: string | undefined, fallback: number) {
    if (!value) {
      return fallback;
    }

    return Math.max(
      0,
      Math.min(lastMonth, monthIndex(value) - baseMonth)
    );
  }

  const initialStart = selectedOffset(createdFrom, 0);
  const initialEnd = selectedOffset(createdTo, lastMonth);

  const [range, setRange] = useState({
    start: Math.min(initialStart, initialEnd),
    end: Math.max(initialStart, initialEnd),
  });

  if (!earliest || !latest) {
    return (
      <div className="date-range date-range-empty">
        No dated artworks
      </div>
    );
  }

  const startPosition = position(range.start, lastMonth);
  const endPosition = position(range.end, lastMonth);
  const singleMonth = lastMonth === 0;

  function commitRange() {
    const changed =
      range.start !== Math.min(initialStart, initialEnd) ||
      range.end !== Math.max(initialStart, initialEnd);

    if (changed) {
      onCommit?.(
        apiMonth(baseMonth + range.start),
        apiMonth(baseMonth + range.end)
      );
    }
  }

  function commitKeyboardChange(key: string) {
    const adjustmentKeys = [
      "ArrowLeft",
      "ArrowRight",
      "ArrowUp",
      "ArrowDown",
      "Home",
      "End",
      "PageUp",
      "PageDown",
    ];

    if (adjustmentKeys.includes(key)) {
      commitRange();
    }
  }

  return (
    <fieldset
      className="date-range"
      aria-label="Completion month range"
      disabled={singleMonth}
    >
      <div className="date-labels">
        <label htmlFor="completion-start">
          <output htmlFor="completion-start">
            {monthLabel(baseMonth + range.start)}
          </output>
        </label>
        <label htmlFor="completion-end">
          <output htmlFor="completion-end">
            {monthLabel(baseMonth + range.end)}
          </output>
        </label>
      </div>

      <div className="range-track">
        <div
          className="range-fill"
          style={{
            left: startPosition,
            width: `calc(${endPosition} - ${startPosition})`,
          }}
        />
        <span
          className="range-handle range-start"
          style={{ left: startPosition }}
          aria-hidden="true"
        />
        <span
          className="range-handle range-end"
          style={{ left: endPosition }}
          aria-hidden="true"
        />

        <input
          id="completion-start"
          className="month-start"
          type="range"
          min={0}
          max={lastMonth}
          step={1}
          value={range.start}
          aria-label="Start completion month"
          aria-valuetext={accessibleMonth(baseMonth + range.start)}
          onPointerUp={commitRange}
          onKeyUp={(event) => commitKeyboardChange(event.key)}
          onChange={(event) => {
            const start = Number(event.target.value);
            setRange((current) => ({
              start,
              end: Math.max(start, current.end),
            }));
          }}
        />
        <input
          id="completion-end"
          className="month-end"
          type="range"
          min={0}
          max={lastMonth}
          step={1}
          value={range.end}
          aria-label="End completion month"
          aria-valuetext={accessibleMonth(baseMonth + range.end)}
          onPointerUp={commitRange}
          onKeyUp={(event) => commitKeyboardChange(event.key)}
          onChange={(event) => {
            const end = Number(event.target.value);
            setRange((current) => ({
              start: Math.min(current.start, end),
              end,
            }));
          }}
        />
      </div>
    </fieldset>
  );
}
