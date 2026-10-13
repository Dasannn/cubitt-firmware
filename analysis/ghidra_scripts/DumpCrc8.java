// DumpCrc8.java - decompiles file_tran crc8 functions and dumps referenced tables.
// Headless: analyzeHeadless <proj> cubitt -process -noanalysis -postScript DumpCrc8.java
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryAccessException;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.listing.Instruction;

public class DumpCrc8 extends GhidraScript {
    long[] targets = { 0x100ac3acL, 0x100ac3d4L };

    private void dumpBytes(Address a, int n) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) {
            try {
                int b = getByte(a.add(i)) & 0xff;
                sb.append(String.format("%02x ", b));
            } catch (Exception e) { sb.append("?? "); }
            if ((i & 15) == 15) sb.append("\n");
        }
        println(sb.toString());
    }

    @Override
    public void run() throws Exception {
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        for (long t : targets) {
            Address a = toAddr(t);
            Function f = getFunctionAt(a);
            if (f == null) { println("== NO FUNC @ 0x" + Long.toHexString(t)); continue; }
            println("==== " + f.getName() + " @ 0x" + Long.toHexString(t) + " ====");
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            if (r != null && r.decompileCompleted())
                println(r.getDecompiledFunction().getC());
            else
                println("(decompile failed)");

            // find data references within the function (possible crc table)
            println("-- data refs in function body --");
            Instruction ins = getInstructionAt(f.getEntryPoint());
            java.util.HashSet<Long> seen = new java.util.HashSet<>();
            while (ins != null && f.getBody().contains(ins.getAddress())) {
                for (Reference ref : ins.getReferencesFrom()) {
                    if (ref.getReferenceType().isData()) {
                        Address da = ref.getToAddress();
                        if (seen.add(da.getOffset())) {
                            println("  ref -> " + da + " @ins " + ins.getAddress());
                            println("  bytes(256) from " + da + ":");
                            dumpBytes(da, 256);
                        }
                    }
                }
                ins = ins.getNext();
            }
        }
        di.dispose();
    }
}
