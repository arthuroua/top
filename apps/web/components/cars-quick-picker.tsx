"use client";

import Link from "next/link";
import { useState } from "react";

import { modelPageHref } from "../lib/seoApi";

type BrandOption = {
  make: string;
  slugPath: string;
  models: string[];
};

type Props = {
  brands: BrandOption[];
  labels: {
    chip: string;
    title: string;
    lead: string;
    make: string;
    model: string;
    chooseModel: string;
    openBrand: string;
    openModel: string;
  };
};

export function CarsQuickPicker({ brands, labels }: Props) {
  const [selectedMake, setSelectedMake] = useState(brands[0]?.make ?? "");
  const [selectedModel, setSelectedModel] = useState(brands[0]?.models[0] ?? "");

  const activeBrand = brands.find((item) => item.make === selectedMake) ?? null;
  const modelOptions = activeBrand?.models ?? [];
  const brandHref = activeBrand ? `/cars/${activeBrand.slugPath}` : "/cars";
  const modelHref = activeBrand && selectedModel ? modelPageHref(activeBrand.make, selectedModel) : brandHref;

  function handleMakeChange(nextMake: string) {
    setSelectedMake(nextMake);
    const nextBrand = brands.find((item) => item.make === nextMake);
    setSelectedModel(nextBrand?.models[0] ?? "");
  }

  return (
    <section className="panel carsQuickPicker">
      <div className="carsQuickPickerIntro">
        <p className="chip">{labels.chip}</p>
        <h2>{labels.title}</h2>
        <p>{labels.lead}</p>
      </div>

      <div className="carsQuickPickerPanel">
        <label>
          <span className="label">{labels.make}</span>
          <select value={selectedMake} onChange={(event) => handleMakeChange(event.target.value)}>
            {brands.map((brand) => (
              <option key={brand.make} value={brand.make}>
                {brand.make}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="label">{labels.model}</span>
          <select
            value={selectedModel}
            onChange={(event) => setSelectedModel(event.target.value)}
            disabled={modelOptions.length === 0}
          >
            {modelOptions.length === 0 ? (
              <option value="">{labels.chooseModel}</option>
            ) : (
              modelOptions.map((model) => (
                <option key={`${selectedMake}-${model}`} value={model}>
                  {model}
                </option>
              ))
            )}
          </select>
        </label>

        <div className="carsQuickPickerActions">
          <Link href={brandHref} className="ghostButton">
            {labels.openBrand}
          </Link>
          <Link href={modelHref} className="button">
            {labels.openModel}
          </Link>
        </div>
      </div>
    </section>
  );
}
