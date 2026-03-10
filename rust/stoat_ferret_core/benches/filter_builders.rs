//! Criterion benchmarks for Phase 2 filter builders.
//!
//! Measures filter string generation performance for drawtext, speed, audio,
//! transition builders, and filter graph validation at varying complexity.
//!
//! Run with: `cargo bench`
//! HTML reports generated in `target/criterion/`

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use stoat_ferret_core::ffmpeg::audio::{AmixBuilder, VolumeBuilder};
use stoat_ferret_core::ffmpeg::drawtext::DrawtextBuilder;
use stoat_ferret_core::ffmpeg::filter::{FilterChain, FilterGraph};
use stoat_ferret_core::ffmpeg::speed::SpeedControl;
use stoat_ferret_core::ffmpeg::transitions::{FadeBuilder, TransitionType, XfadeBuilder};

fn bench_drawtext(c: &mut Criterion) {
    c.bench_function("drawtext_basic", |b| {
        b.iter(|| {
            DrawtextBuilder::new(black_box("Hello World"))
                .fontsize(24)
                .fontcolor("white")
                .build()
        });
    });

    c.bench_function("drawtext_full", |b| {
        b.iter(|| {
            DrawtextBuilder::new(black_box("Title: Special Ch@rs & 'quotes'"))
                .fontsize(48)
                .fontcolor("yellow")
                .shadow(2, 2, "black")
                .box_background("black@0.5", 5)
                .alpha_fade(0.0, 1.0, 10.0, 1.0)
                .enable("between(t,1,9)")
                .build()
        });
    });
}

fn bench_speed(c: &mut Criterion) {
    c.bench_function("speed_2x_setpts", |b| {
        let ctrl = SpeedControl::new(black_box(2.0)).unwrap();
        b.iter(|| ctrl.setpts_filter());
    });

    c.bench_function("speed_2x_atempo", |b| {
        let ctrl = SpeedControl::new(black_box(2.0)).unwrap();
        b.iter(|| ctrl.atempo_filters());
    });

    c.bench_function("speed_0.25x_atempo_chain", |b| {
        let ctrl = SpeedControl::new(black_box(0.25)).unwrap();
        b.iter(|| ctrl.atempo_filters());
    });

    c.bench_function("speed_4x_atempo_chain", |b| {
        let ctrl = SpeedControl::new(black_box(4.0)).unwrap();
        b.iter(|| ctrl.atempo_filters());
    });
}

fn bench_audio_mix(c: &mut Criterion) {
    c.bench_function("amix_2_inputs", |b| {
        let builder = AmixBuilder::new(black_box(2)).unwrap();
        b.iter(|| builder.build());
    });

    c.bench_function("amix_4_inputs_weighted", |b| {
        let builder = AmixBuilder::new(black_box(4))
            .unwrap()
            .with_weights(&[1.0, 0.5, 0.5, 0.3])
            .with_duration_mode("longest");
        b.iter(|| builder.build());
    });
}

fn bench_volume(c: &mut Criterion) {
    c.bench_function("volume_linear", |b| {
        let builder = VolumeBuilder::new(black_box(0.5)).unwrap();
        b.iter(|| builder.build());
    });

    c.bench_function("volume_db", |b| {
        let builder = VolumeBuilder::new_db(black_box("-6dB")).unwrap();
        b.iter(|| builder.build());
    });
}

fn bench_fade(c: &mut Criterion) {
    c.bench_function("fade_in", |b| {
        let builder = FadeBuilder::new(black_box("in"), black_box(1.5)).unwrap();
        b.iter(|| builder.build());
    });

    c.bench_function("fade_out_with_start", |b| {
        let builder = FadeBuilder::new(black_box("out"), black_box(2.0))
            .unwrap()
            .with_start_time(8.0)
            .with_color("white");
        b.iter(|| builder.build());
    });
}

fn bench_xfade(c: &mut Criterion) {
    c.bench_function("xfade_fade", |b| {
        let builder = XfadeBuilder::new(
            black_box(TransitionType::Fade),
            black_box(1.0),
            black_box(5.0),
        )
        .unwrap();
        b.iter(|| builder.build());
    });

    c.bench_function("xfade_wipeleft", |b| {
        let builder = XfadeBuilder::new(
            black_box(TransitionType::Wipeleft),
            black_box(0.5),
            black_box(3.0),
        )
        .unwrap();
        b.iter(|| builder.build());
    });
}

/// Build a filter graph with `n` linear chains for validation benchmarking.
fn make_graph(chain_count: usize) -> FilterGraph {
    let mut graph = FilterGraph::new();
    for i in 0..chain_count {
        let input_label = if i == 0 {
            "0:v".to_string()
        } else {
            format!("v{}", i - 1)
        };
        let output_label = format!("v{i}");

        graph = graph.chain(
            FilterChain::new()
                .input(input_label)
                .filter(
                    DrawtextBuilder::new(&format!("chain {i}"))
                        .fontsize(24)
                        .build(),
                )
                .output(output_label),
        );
    }
    graph
}

fn bench_filter_graph_validate(c: &mut Criterion) {
    let graph_1 = make_graph(1);
    let graph_5 = make_graph(5);
    let graph_10 = make_graph(10);

    c.bench_function("filter_graph_validate_1_chain", |b| {
        b.iter(|| graph_1.validate());
    });

    c.bench_function("filter_graph_validate_5_chains", |b| {
        b.iter(|| graph_5.validate());
    });

    c.bench_function("filter_graph_validate_10_chains", |b| {
        b.iter(|| graph_10.validate());
    });
}

criterion_group!(
    benches,
    bench_drawtext,
    bench_speed,
    bench_audio_mix,
    bench_volume,
    bench_fade,
    bench_xfade,
    bench_filter_graph_validate,
);
criterion_main!(benches);
