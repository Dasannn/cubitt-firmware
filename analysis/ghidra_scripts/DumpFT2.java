// DumpFT2.java - decompila funciones que contienen direcciones dadas (handlers file_tran).
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;

public class DumpFT2 extends GhidraScript {
    long[] addrs = { 0x10100fc8L, 0x10123812L };
    DecompInterface di;

    private String dc(Function f) {
        DecompileResults r = di.decompileFunction(f, 120, monitor);
        if (r != null && r.decompileCompleted()) return r.getDecompiledFunction().getC();
        return "(decompile failed)";
    }

    @Override
    public void run() throws Exception {
        di = new DecompInterface();
        di.toggleCCode(true);
        di.openProgram(currentProgram);
        for (long a : addrs) {
            Address ad = toAddr(a);
            Function f = getFunctionContaining(ad);
            if (f == null) {
                // intenta disasm + crear funcion en esa direccion
                disassemble(ad);
                f = createFunction(ad, null);
                if (f == null) f = getFunctionContaining(ad);
            }
            if (f == null) { println("\n==== NO FUNC containing 0x" + Long.toHexString(a) + " ===="); continue; }
            println("\n==== " + f.getName() + " @ " + f.getEntryPoint() + " (target 0x" + Long.toHexString(a) + ") ====");
            println(dc(f));
        }
        di.dispose();
    }
}
